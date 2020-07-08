from zou.app.models.file_status import FileStatus
from zou.app import app

from zou.app.models.output_file import OutputFile
from zou.app.models.output_type import OutputType
from zou.app.models.preview_file import PreviewFile
from zou.app.models.project import Project
from zou.app.models.software import Software
from zou.app.models.task import Task

from zou.app.services.base_service import (
    get_instance,
    get_or_create_instance_by_name,
)

from zou.app.services.exception import (
    OutputFileNotFoundException,
    OutputTypeNotFoundException,
    PreviewFileNotFoundException,
    SoftwareNotFoundException,
    NoOutputFileException,
    EntryAlreadyExistsException,
)

from zou.app.utils import cache, fields, events, query as query_utils

from sqlalchemy import desc, func
from sqlalchemy.exc import StatementError, IntegrityError
from sqlalchemy.sql.expression import and_

from zou.app.services.files_sub_service import *


def clear_preview_file_cache(preview_file_id):
    cache.cache.delete_memoized(get_preview_file, preview_file_id)


def get_default_status():
    """
    Return default file status to set on a file when it is created.
    """
    default_status = FileStatus.get_by(name=app.config["DEFAULT_FILE_STATUS"])
    if default_status is None:
        default_status = FileStatus(
            name=app.config["DEFAULT_FILE_STATUS"], color="#FFFFFF"
        )
        default_status.save()
    return default_status.serialize()


def get_output_file_raw(output_file_id):
    """
    Return given output file as active record.
    """
    return get_instance(OutputFile, output_file_id, OutputFileNotFoundException)


def get_output_file(output_file_id):
    """
    Return given output file as a dict.
    """
    return get_output_file_raw(output_file_id).serialize()


def get_software_raw(software_id):
    """
    Return given software as active record.
    """
    return get_instance(Software, software_id, SoftwareNotFoundException)


def get_software(software_id):
    """
    Return given software as dict.
    """
    return get_software_raw(software_id).serialize()


def get_output_type_raw(output_type_id):
    """
    Return given output type as active record.
    """
    return get_instance(OutputType, output_type_id, OutputTypeNotFoundException)


def get_output_type(output_type_id):
    """
    Return given output type as dict.
    """
    return get_output_type_raw(output_type_id).serialize()


def get_or_create_output_type(name, short_name=""):
    return get_or_create_instance_by_name(
        OutputType, name=name, short_name=short_name
    )


def get_or_create_software(name, short_name, file_extension):
    return get_or_create_instance_by_name(
        Software,
        name=name,
        short_name=short_name,
        file_extension=file_extension,
    )


def create_new_output_revision(
    entity_id,
    working_file_id,
    output_type_id,
    person_id,
    task_type_id,
    revision=0,
    representation="",
    name="main",
    comment="",
    extension="",
    path="",
    nb_elements=1,
    frame_start=1,
    asset_instance_id=None,
    temporal_entity_id=None,
    file_status_id=None
):
    """
    Create a new ouput file for given entity. Output type, task type, author
    and source file are required.

    The revision is set as next revision available but it can be forced.
    An extension and a name can be set too.

    An asset instance can be given too. In that case, the output file is
    linked to the asset instance.

    The `temporal_entity_id` concerns only asset instance output files. It is
    here to describe if the output is generated in the context of a shot or in
    the context of a scene.
    """

    if revision < 1:
        try:
            output_file = get_last_output_revision(
                entity_id,
                output_type_id,
                task_type_id,
                name=name,
                asset_instance_id=asset_instance_id,
                temporal_entity_id=temporal_entity_id,
            )

            revision = output_file["revision"] + 1
        except NoOutputFileException:
            revision = 1

    file_status_id = file_status_id or get_default_status()["id"]

    try:
        output_file = OutputFile.get_by(
            name=name,
            entity_id=entity_id,
            asset_instance_id=asset_instance_id,
            output_type_id=output_type_id,
            task_type_id=task_type_id,
            temporal_entity_id=temporal_entity_id,
            representation=representation,
            revision=revision,
        )

        if output_file is None:
            output_file = OutputFile.create(
                name=name,
                comment=comment,
                extension=extension,
                path=path,
                representation=representation,
                revision=revision,
                entity_id=entity_id,
                asset_instance_id=asset_instance_id,
                person_id=person_id,
                source_file_id=working_file_id,
                output_type_id=output_type_id,
                file_status_id=file_status_id,
                task_type_id=task_type_id,
                nb_elements=nb_elements,
                frame_start=frame_start,
                temporal_entity_id=temporal_entity_id,
            )
            events.emit("output_file:new", {"output_file_id": output_file.id})
        else:
            raise EntryAlreadyExistsException

    except IntegrityError:
        raise EntryAlreadyExistsException

    return output_file.serialize()


def get_next_output_file_revision(
    entity_id,
    output_type_id,
    task_type_id,
    name="main",
    asset_instance_id=None,
    temporal_entity_id=None,
):
    """
    Get next output file revision available for given entity, output type, task
    type and name.
    Asset instance can be set, in that case, it looks for next revision
    available for it instead of entity.
    """
    try:
        last_output = get_last_output_revision(
            output_type_id=output_type_id,
            task_type_id=task_type_id,
            entity_id=entity_id,
            name=name,
            asset_instance_id=asset_instance_id,
            temporal_entity_id=temporal_entity_id,
        )
        return last_output["revision"] + 1
    except NoOutputFileException:
        return 1


def get_last_output_revision(
    entity_id,
    output_type_id,
    task_type_id,
    name="main",
    asset_instance_id=None,
    temporal_entity_id=None,
):
    """
    Get output with highest revision created for given entity, output type, task
    type and name.
    If an asset instance is given, it will look for last output file for this
    instance instead of given entity.
    """
    query = (
        OutputFile.query.filter_by(
            output_type_id=output_type_id, task_type_id=task_type_id, name=name
        )
        .filter(OutputFile.revision > 0)
        .order_by(desc(OutputFile.revision))
    )

    if asset_instance_id is None:
        query = query.filter(OutputFile.entity_id == entity_id)
    else:
        query = query.filter(
            OutputFile.asset_instance_id == asset_instance_id,
            OutputFile.temporal_entity_id == temporal_entity_id,
        )

    output_files = query.all()

    if len(output_files) == 0:
        raise NoOutputFileException()

    return output_files[0].serialize()


def get_output_files_for_entity(
    entity_id,
    task_type_id=None,
    output_type_id=None,
    name=None,
    representation=None,
    file_status_id=None,
):
    """
    Return output files for given entity ordered by revision.
    """
    query = OutputFile.query.filter_by(entity_id=entity_id)

    if task_type_id:
        query = query.filter(OutputFile.task_type_id == task_type_id)
    if output_type_id:
        query = query.filter(OutputFile.output_type_id == output_type_id)
    if name:
        query = query.filter(OutputFile.name == name)
    if representation:
        query = query.filter(OutputFile.representation == representation)
    if file_status_id:
        query = query.filter(OutputFile.file_status_id == file_status_id)

    query = query.filter(OutputFile.asset_instance_id == None)
    query = query.filter(OutputFile.temporal_entity_id == None)

    output_files = (
        query.filter(OutputFile.revision >= 0)
        .order_by(desc(OutputFile.revision))
        .all()
    )
    return fields.serialize_models(output_files)


def get_output_files_for_instance(
    asset_instance_id,
    temporal_entity_id,
    task_type_id=None,
    output_type_id=None,
    name=None,
    representation=None,
    file_status_id=None,
):
    """
    Return output files for given instance ordered by revision.
    """
    query = OutputFile.query.filter_by(asset_instance_id=asset_instance_id)

    if temporal_entity_id:
        query = query.filter(
            OutputFile.temporal_entity_id == temporal_entity_id
        )
    if task_type_id:
        query = query.filter(OutputFile.task_type_id == task_type_id)
    if output_type_id:
        query = query.filter(OutputFile.output_type_id == output_type_id)
    if name:
        query = query.filter(OutputFile.name == name)
    if representation:
        query = query.filter(OutputFile.representation == representation)
    if file_status_id:
        query = query.filter(OutputFile.file_status_id == file_status_id)

    output_files = (
        query.filter(OutputFile.revision >= 0)
        .order_by(desc(OutputFile.revision))
        .all()
    )
    return fields.serialize_models(output_files)


def get_last_output_files_for_entity(
    entity_id,
    task_type_id=None,
    output_type_id=None,
    name=None,
    representation=None,
    file_status_id=None,
):
    """
    Get last output files for given parameters.

    We use a subquery to get maximum revision and then filter with given
    params.
    """
    # Query maximum revision for each possible arguments.
    # Only group and filter by file status if specified. Otherwise this could
    # lead to different groups of files sharing the same history but with
    # different status.
    # This could be very misleading when the user would want to get the last.
    if file_status_id:
        query = OutputFile.query.with_entities(
            OutputFile.task_type_id,
            OutputFile.output_type_id,
            OutputFile.name,
            OutputFile.representation,
            OutputFile.file_status_id,
            func.max(OutputFile.revision).label("MAX"),
        ).group_by(
            OutputFile.task_type_id,
            OutputFile.output_type_id,
            OutputFile.name,
            OutputFile.representation,
            OutputFile.file_status_id,
        )
    else:
        query = OutputFile.query.with_entities(
            OutputFile.task_type_id,
            OutputFile.output_type_id,
            OutputFile.name,
            OutputFile.representation,
            func.max(OutputFile.revision).label("MAX"),
        ).group_by(
            OutputFile.task_type_id,
            OutputFile.output_type_id,
            OutputFile.name,
            OutputFile.representation,
        )

    query = query.filter(OutputFile.entity_id == entity_id)
    query = query.filter(OutputFile.asset_instance_id == None)
    if file_status_id:
        query = query.filter(OutputFile.file_status_id == file_status_id)
    statement = query.subquery()

    # Create a join query to retrieve maximum revision and filter by
    # specified arguments
    query = OutputFile.query.join(
        statement,
        and_(
            OutputFile.task_type_id == statement.c.task_type_id,
            OutputFile.output_type_id == statement.c.output_type_id,
            OutputFile.name == statement.c.name,
            OutputFile.representation == statement.c.representation,
            OutputFile.revision == statement.c.MAX,
        ),
    )

    # Filter by specified arguments
    if task_type_id:
        query = query.filter(OutputFile.task_type_id == task_type_id)
    if output_type_id:
        query = query.filter(OutputFile.output_type_id == output_type_id)
    if name:
        query = query.filter(OutputFile.name == name)
    if representation:
        query = query.filter(OutputFile.representation == representation)

    query = query.filter(OutputFile.entity_id == entity_id)
    query = query.filter(OutputFile.asset_instance_id == None)

    # query
    output_files = query.all()
    return fields.serialize_models(output_files)


def get_last_output_files_for_instance(
    asset_instance_id,
    temporal_entity_id,
    task_type_id=None,
    output_type_id=None,
    name=None,
    representation=None,
    file_status_id=None,
):
    """
    Get last output files for given entity grouped by output type and name.
    """
    # Query maximum revision for each possible arguments
    # Only group and filter by file status if specified. Otherwise this could
    # lead to different groups of files sharing the same history but with
    # different status.
    # This could be very misleading when the user would want to get the last.
    if file_status_id:
        query = OutputFile.query.with_entities(
            OutputFile.temporal_entity_id,
            OutputFile.task_type_id,
            OutputFile.output_type_id,
            OutputFile.name,
            OutputFile.representation,
            OutputFile.file_status_id,
            func.max(OutputFile.revision).label("MAX"),
        ).group_by(
            OutputFile.temporal_entity_id,
            OutputFile.task_type_id,
            OutputFile.output_type_id,
            OutputFile.name,
            OutputFile.representation,
            OutputFile.file_status_id,
        )
    else:
        query = OutputFile.query.with_entities(
            OutputFile.temporal_entity_id,
            OutputFile.task_type_id,
            OutputFile.output_type_id,
            OutputFile.name,
            OutputFile.representation,
            func.max(OutputFile.revision).label("MAX"),
        ).group_by(
            OutputFile.temporal_entity_id,
            OutputFile.task_type_id,
            OutputFile.output_type_id,
            OutputFile.name,
            OutputFile.representation,
        )
    query = query.filter(OutputFile.asset_instance_id == asset_instance_id)
    query = query.filter(OutputFile.temporal_entity_id == temporal_entity_id)
    if file_status_id:
        query = query.filter(OutputFile.file_status_id == file_status_id)
    statement = query.subquery()

    # Create a join query to retrieve maximum revision
    query = OutputFile.query.join(
        statement,
        and_(
            OutputFile.temporal_entity_id == statement.c.temporal_entity_id,
            OutputFile.task_type_id == statement.c.task_type_id,
            OutputFile.output_type_id == statement.c.output_type_id,
            OutputFile.name == statement.c.name,
            OutputFile.representation == statement.c.representation,
            OutputFile.revision == statement.c.MAX,
        ),
    )

    # Filter by specified arguments
    query = query.filter(OutputFile.asset_instance_id == asset_instance_id)
    query = query.filter(OutputFile.temporal_entity_id == temporal_entity_id)
    if task_type_id:
        query = query.filter(OutputFile.task_type_id == task_type_id)
    if output_type_id:
        query = query.filter(OutputFile.output_type_id == output_type_id)
    if name:
        query = query.filter(OutputFile.name == name)
    if representation:
        query = query.filter(OutputFile.representation == representation)
    if representation:
        query = query.filter(OutputFile.file_status_id == file_status_id)

    output_files = query.all()
    return fields.serialize_models(output_files)


def get_preview_file_raw(preview_file_id):
    """
    Get preview file as active record.
    """
    try:
        preview_file = PreviewFile.get(preview_file_id)
    except StatementError:
        raise PreviewFileNotFoundException()

    if preview_file is None:
        raise PreviewFileNotFoundException()

    return preview_file


@cache.memoize_function(240)
def get_preview_file(preview_file_id):
    """
    Get preview file as dict.
    """
    preview_file = get_preview_file_raw(preview_file_id)
    return preview_file.serialize()


def get_preview_files_for_task(task_id):
    """
    Get all preview files for given task.
    """
    previews = PreviewFile.filter_by(task_id=task_id).order_by(
        PreviewFile.revision.desc()
    )
    return fields.serialize_models(previews)


def create_preview_file_raw(
    name, revision, task_id, person_id, source="webgui", extension="mp4"
):
    return PreviewFile.create(
        name=name,
        revision=revision,
        source=source,
        task_id=task_id,
        person_id=person_id,
        extension=extension,
    )


def create_preview_file(
    name, revision, task_id, person_id, source="webgui", extension="mp4"
):
    return create_preview_file_raw(
        name, revision, task_id, person_id, source, extension
    ).serialize()




def update_output_file(output_file_id, data):
    output_file = get_output_file_raw(output_file_id)
    output_file.update(data)
    return output_file.serialize()


def update_preview_file(preview_file_id, data):
    preview_file = get_preview_file_raw(preview_file_id)
    preview_file.update(data)
    clear_preview_file_cache(preview_file_id)
    events.emit("preview-file:update", {"preview_file_id": preview_file_id})
    return preview_file.serialize()


def get_output_types_for_entity(entity_id):
    """
    Get output types from all output files created for given entity.
    """
    output_types = (
        OutputType.query.join(OutputFile)
        .filter(OutputFile.entity_id == entity_id)
        .order_by(OutputType.name)
        .all()
    )
    return OutputType.serialize_list(output_types)


def get_output_types_for_instance(asset_instance_id, temporal_entity_id=None):
    """
    Get output types from all output files created for given instance.
    """
    output_types = (
        OutputType.query.join(OutputFile)
        .filter(
            OutputFile.asset_instance_id == asset_instance_id,
            OutputFile.temporal_entity_id == temporal_entity_id,
        )
        .order_by(OutputType.name)
        .all()
    )
    return OutputType.serialize_list(output_types)


def get_output_files_for_output_type_and_entity(
    entity_id, output_type_id, representation=None
):
    """
    Get output files created for given entity and output type.
    """
    query = (
        OutputFile.query.filter(OutputFile.entity_id == entity_id)
        .filter(OutputFile.asset_instance_id == None)  # noqa Entity only
        .filter(OutputFile.output_type_id == output_type_id)
        .order_by(desc(OutputFile.revision))
    )

    if representation is not None:
        query = query.filter(OutputFile.representation == representation)

    output_files = query.all()
    return OutputFile.serialize_list(output_files)


def get_output_files_for_output_type_and_asset_instance(
    asset_instance_id, temporal_entity_id, output_type_id, representation=None
):
    """
    Get output files created for given asset instance and output type.
    """
    query = OutputFile.query.filter(
        OutputFile.asset_instance_id == asset_instance_id,
        OutputFile.output_type_id == output_type_id,
        OutputFile.temporal_entity_id == temporal_entity_id,
    ).order_by(desc(OutputFile.revision))

    if representation is not None:
        query = query.filter(OutputFile.representation == representation)

    output_files = query.all()
    return OutputFile.serialize_list(output_files)


def remove_preview_file(preview_file_id):
    preview_file = get_preview_file_raw(preview_file_id)
    preview_file.delete()
    events.emit("preview_file:delete", {"preview_file_id": preview_file_id})
    return preview_file.serialize()


def get_project_from_preview_file(preview_file_id):
    """
    Get project dict of related preview file.
    """
    preview_file = get_preview_file_raw(preview_file_id)
    task = Task.get(preview_file.task_id)
    project = Project.get(task.project_id)
    return project.serialize()


def get_preview_files_for_project(project_id, page=-1):
    """
    Return all preview files for given project.
    """
    query = (
        PreviewFile.query.join(Task)
        .filter(Task.project_id == project_id)
        .order_by(desc(PreviewFile.updated_at))
    )
    return query_utils.get_paginated_results(query, page)
