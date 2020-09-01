from zou.app import db

from zou.app.models.attachment_file import AttachmentFile
from zou.app.models.comment import (
    Comment,
    acknowledgements_table,
    mentions_table,
    preview_link_table
)
from zou.app.services import (
    base_service,
    persons_service,
    tasks_service
)
from zou.app.services.exception import (
    AttachmentFileNotFoundException
)
from zou.app.models.person import Person
from zou.app.models.preview_file import PreviewFile
from zou.app.models.task_status import TaskStatus

from zou.app.utils import cache, events, fs, fields
from zou.app.stores import file_store
from zou.app import config


def get_attachment_file_raw(attachment_file_id):
    return base_service.get_instance(
        AttachmentFile,
        attachment_file_id,
        AttachmentFileNotFoundException
    )


@cache.memoize_function(120)
def get_attachment_file(attachment_file_id):
    """
    Return attachment file model matching given id.
    """
    attachment_file = get_attachment_file_raw(attachment_file_id)
    return attachment_file.serialize()


def get_attachment_file_path(attachment_file):
    return fs.get_file_path(
        config,
        file_store.get_local_file_path,
        file_store.open_file,
        "attachments",
        attachment_file["id"],
        attachment_file["extension"]
    )


def acknowledge_comment(comment_id):
    """
    Add current user to the list of people who acknowledged given comment.
    If he's already present, remove it.
    """
    comment = tasks_service.get_comment_raw(comment_id)
    current_user = persons_service.get_current_user_raw()
    current_user_id = str(current_user.id)

    acknowledgements = fields.serialize_orm_arrays(comment.acknowledgements)
    is_already_ack = current_user_id in acknowledgements

    if is_already_ack:
        _unack_comment(comment, current_user)
    else:
        _ack_comment(comment, current_user)
    comment.save()
    return comment.serialize(relations=True)


def _ack_comment(comment, user):
    user_id = str(user.id)
    comment.acknowledgements.append(user)
    _send_ack_event(comment, user_id, "acknowledge")


def _unack_comment(comment, user):
    user_id = str(user.id)
    comment.acknowledgements = [
        person
        for person in comment.acknowledgements
        if str(person.id) != user_id
    ]
    _send_ack_event(comment, user_id, "unacknowledge")


def _send_ack_event(comment, user_id, name="acknowledge"):
    events.emit("comment:%s" % name, {
        "comment_id": str(comment.id),
        "person_id": user_id
    }, persist=False)


def _prepare_query(object_id, object_type, is_client, is_manager):
    if object_type == "Task":
        query = (
            Comment.query
            .order_by(Comment.created_at.desc())
            .filter_by(object_id=object_id)
            .join(Person, TaskStatus)
            .add_columns(
                TaskStatus.name,
                TaskStatus.short_name,
                TaskStatus.color,
                Person.first_name,
                Person.last_name,
                Person.has_avatar,
            )
        )
    else:
        query = (
            Comment.query
            .order_by(Comment.created_at.desc())
            .filter_by(object_id=object_id)
            .join(Person)
            .add_columns(
                Person.first_name,
                Person.last_name,
                Person.has_avatar,
            )
        )
    if is_client:
        query = query.filter(Person.role == "client")
    if not is_client and not is_manager:
        query = query.filter(Person.role != "client")
    return query


def _run_task_comments_query(query):
    comment_ids = []
    comments = []
    for result in query.all():
        # Task
        if result.__len__() == 7:
            task = True
            (
                comment,
                task_status_name,
                task_status_short_name,
                task_status_color,
                person_first_name,
                person_last_name,
                person_has_avatar,
            ) = result
        else:
            task = False
            (
                comment,
                person_first_name,
                person_last_name,
                person_has_avatar,
            ) = result

        comment_dict = comment.serialize()
        comment_dict["person"] = {
            "first_name": person_first_name,
            "last_name": person_last_name,
            "has_avatar": person_has_avatar,
            "id": str(comment.person_id),
        }
        if task:
            comment_dict["task_status"] = {
                "name": task_status_name,
                "short_name": task_status_short_name,
                "color": task_status_color,
                "id": str(comment.task_status_id),
            }
        comments.append(comment_dict)
        comment_ids.append(comment_dict["id"])
    return (comments, comment_ids)
    

def _build_ack_map_for_comments(comment_ids):
    ack_map = {}
    for link in (
        db.session
        .query(acknowledgements_table)
        .filter(acknowledgements_table.c.comment.in_(comment_ids))
        .all()
    ):
        comment_id = str(link.comment)
        person_id = str(link.person)
        if comment_id not in ack_map:
            ack_map[comment_id] = []
        ack_map[comment_id].append(person_id)
    return ack_map


def _build_mention_map_for_comments(comment_ids):
    mention_map = {}
    for link in (
        db.session
        .query(mentions_table)
        .filter(mentions_table.c.comment.in_(comment_ids))
        .all()
    ):
        comment_id = str(link.comment)
        person_id = str(link.person)
        if comment_id not in mention_map:
            mention_map[comment_id] = []
        mention_map[comment_id].append(person_id)
    return mention_map


def _build_preview_map_for_comments(comment_ids):
    preview_map = {}
    query = (
        PreviewFile.query
        .join(preview_link_table)
        .filter(preview_link_table.c.comment.in_(comment_ids))
        .add_column(preview_link_table.c.comment)
    )
    for (preview, comment_id) in query.all():
        comment_id = str(comment_id)
        if comment_id not in preview_map:
            preview_map[comment_id] = []
        preview_map[comment_id].append({
            "id": str(preview.id),
            "revision": preview.revision,
            "extension": preview.extension,
            "annotations": preview.annotations,
        })
    return preview_map


def _build_attachment_map_for_comments(comment_ids):
    attachment_file_map = {}
    attachment_files = (
        AttachmentFile.query
        .filter(AttachmentFile.comment_id.in_(comment_ids))
        .all()
    )
    for attachment_file in attachment_files:
        comment_id = str(attachment_file.comment_id)
        attachment_file_id = str(attachment_file.id)
        if comment_id not in attachment_file_map:
            attachment_file_map[str(comment_id)] = []
        attachment_file_map[str(comment_id)].append({
            "id": attachment_file_id,
            "name": attachment_file.name,
            "extension": attachment_file.extension,
            "size": attachment_file.size
        })
    return attachment_file_map

