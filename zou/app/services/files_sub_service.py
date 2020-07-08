import os
import itertools
from operator import itemgetter

from zou.app.models.file_status import FileStatus
from zou.app import app

from zou.app.models.output_file import OutputFile
from zou.app.models.working_file import WorkingFile
from zou.app.models.dependent_file import DependentFile
from zou.app.models.children_file import ChildrenFile
from zou.app.models.task import Task

from zou.app.services.base_service import (
    get_instance,
    get_or_create_instance_by_name,
)


from zou.app.services.exception import (
    WorkingFileNotFoundException,
    EntryAlreadyExistsException,
    OutputFileNotFoundException
)


from zou.app.utils import cache, fields, events, query as query_utils

from sqlalchemy import desc, func
from sqlalchemy.exc import StatementError, IntegrityError
from sqlalchemy.sql.expression import and_


def get_working_file_raw(working_file_id):
    """
    Return given working file as active record.
    """
    return get_instance(
        WorkingFile, working_file_id, WorkingFileNotFoundException
    )


def get_working_file(working_file_id):
    """
    Return given working file as dict.
    """
    return get_working_file_raw(working_file_id).serialize()


def update_working_file(working_file_id, data):
    working_file = get_working_file_raw(working_file_id)
    working_file.update(data)
    return working_file.serialize()


def get_last_working_files_for_task(task_id):
    """
    Get last revisions for given task grouped by file name.
    """
    query = WorkingFile.query.with_entities(
        WorkingFile.name,
        WorkingFile.task_id,
        func.max(WorkingFile.revision).label("MAX"),
    ).group_by(
        WorkingFile.name,
        WorkingFile.task_id,
    )

    query = query.filter(WorkingFile.task_id == task_id)
    statement = query.subquery()

    query = WorkingFile.query.join(
        statement,
        and_(
            WorkingFile.task_id == statement.c.task_id,
            WorkingFile.name == statement.c.name,
            WorkingFile.revision == statement.c.MAX,
        ),
    )

    # query
    working_files = fields.serialize_models(query.all())

    # group by name
    working_files_by_name = {
        k: list(v)[0]
        for k, v
        in itertools.groupby(working_files, key=itemgetter('name'))}

    return working_files_by_name


def get_next_working_revision(task_id, name):
    """
    Get next working file revision for given task and name.
    """
    working_files = (
        WorkingFile.query.filter_by(task_id=task_id, name=name)
        .order_by(desc(WorkingFile.revision))
        .all()
    )
    if len(working_files) > 0:
        revision = working_files[0].revision + 1
    else:
        revision = 1
    return revision


def create_new_working_revision(
    task_id,
    person_id,
    software_id,
    name="main",
    path="",
    comment="",
    revision=0,
):
    """
    Create a new working file revision for given task. An author (user) and
    a software are required.
    """
    task = Task.get(task_id)
    if revision == 0:
        revision = get_next_working_revision(task_id, name)

    try:
        working_file = WorkingFile.create(
            comment=comment,
            name=name,
            revision=revision,
            path=path,
            task_id=task.id,
            software_id=software_id,
            entity_id=task.entity_id,
            person_id=person_id,
        )
        events.emit("working_file:new", {"working_file_id": working_file.id})
    except IntegrityError:
        raise EntryAlreadyExistsException

    return working_file.serialize()


def get_working_files_for_task(task_id):
    """
    Retrieve all working files for a given task ordered by revision from
    biggest to smallest revision.
    """
    working_files = (
        WorkingFile.query.filter_by(task_id=task_id)
        .filter(WorkingFile.revision >= 0)
        .order_by(desc(WorkingFile.revision))
        .all()
    )
    return fields.serialize_models(working_files)


def get_working_files_for_entity(entity_id, task_id=None, name=None):
    """
    Retrieve all working files for a given entity and specified parameters
    ordered by revision from biggest to smallest revision.
    """
    query = WorkingFile.query.filter_by(entity_id=entity_id)

    if task_id:
        query = query.filter(WorkingFile.task_id == task_id)
    if name:
        query = query.filter(WorkingFile.name == name)

    query = query.filter(WorkingFile.revision >= 0).order_by(
        desc(WorkingFile.revision)
    )

    working_files = query.all()
    return fields.serialize_models(working_files)


def get_next_working_file_revision(task_id, name):
    """
    Get next working file revision available for given task and given name.
    """
    last_working_files = get_last_working_files_for_task(task_id)
    working_file = last_working_files.get(name, None)
    if working_file is not None:
        revision = working_file["revision"] + 1
    else:
        revision = 1
    return revision

