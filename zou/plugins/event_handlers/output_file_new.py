import os
import logging

from zou.app.models.output_file import OutputFile
from zou.app.models.output_type import OutputType
from zou.app.models.children_file import ChildrenFile
from zou.app.models.file_status import FileStatus
from zou.app.celery import celery

from . import generate_children

logger = logging.getLogger(__name__)
IMAGE_EXT = [
    "mov",
    "mp4",
    "r3d",
    "avi",
    "webm",
    "mkv",
    "mpg",
    "mxf",
    "dpx",
    "ari",
    "exr",
    "jpg",
    "jpeg",
    "png",
    "tga",
    "tif",
    "tiff",
    "bmp",
    "psd",
]


def make_children(output_file, children_type):
    print("make_children", children_type)
    # already existing
    for children in output_file.children_files:
        if children.output_type.name == children_type:
            return

    children_file = ChildrenFile.create(
        parent_file_id=output_file.id,
        output_type_id=OutputType.get_by(name=children_type).id,
        file_status_id=FileStatus.get_by(name="PENDING").id,
    )
    
    # maybe emit event here
    generate_children.handle_event.delay({"children_file_id": children_file.id})


@celery.task
def handle_event(data):
    print("HANDLE OUTPUT")
    output_file = OutputFile.get(data.get("output_file_id"))
    # file deleted or unreachable
    if not output_file:
        print("failed find file")
        logger.info(f"Missing output_file: {data}")
        return

    # ignore in render file
    if FileStatus.get(output_file.file_status_id).name == "IN RENDER":
        print("bad status")
        return
    
    # default for all files
    # TODO: fix this -> remove [100-200]
    path = output_file.path
    if "%" in path:
        path = " ".join(output_file.path.split(" ")[:-1])
    ext = os.path.splitext(path)[1][1:].lower()
    if not ext or ext not in IMAGE_EXT:
        print("bad ext")
        return

    output_type = OutputType.get(output_file.output_type_id).name
    make_children(output_file, "thumb_high")
    make_children(output_file, "thumb_low")
    make_children(output_file, "review_web")

    if output_type in ["comp_render", "cgi_render"]:
        make_children(output_file, "review_high")
        make_children(output_file, "proxy_exr")

    elif output_type in ["plate"]:
        make_children(output_file, "proxy_exr")

    elif output_type in ["edit"]:
        make_children(output_file, "review_high")
