from flask import Blueprint

from zou.app.utils.api import configure_api_from_blueprint

from .resources import (
    AckCommentResource,
    CommentTaskResource,
    DownloadAttachmentResource,
    CommentFileResource
)


routes = [
    ("/data/tasks/<task_id>/comments/<comment_id>/ack", AckCommentResource),
    (
        "/data/attachment-files/<attachment_file_id>/file",
        DownloadAttachmentResource
    ),
    ("/actions/tasks/<task_id>/comment", CommentTaskResource),
    ("/actions/files/<file_id>/comment", CommentFileResource),
]

blueprint = Blueprint("comments", "comments")
api = configure_api_from_blueprint(blueprint, routes)
