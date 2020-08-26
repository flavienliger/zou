import os
import subprocess
import tempfile
import logging
from typing import Optional

from zou.app import app
from zou.app.models.children_file import ChildrenFile
from zou.app.models.file_status import FileStatus
from zou.app.stores import file_store
from zou.app.utils.dd import remap_path
from zou.app.celery import celery

logger = logging.getLogger(__name__)
STATUS_RENDER = FileStatus.get_by(name="IN RENDER")
STATUS_FAILED = FileStatus.get_by(name="FAILED")
STATUS_SUCCESS = FileStatus.get_by(name="GENERATED")
IMAGE_EXT = [
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
    "sgi",
    "psd",
]

# -------------------------

def get_temp_file(suffix: str = None) -> str:
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir="tmp", suffix=suffix)
    temp_file.close()
    file_path = temp_file.name
    return file_path

def get_image_metadata(file_path: str) -> dict:
    return cmd_execute(f"oiiotool '{file_path}'")

def oiiotool_get_size(file_path: str) -> int:
    metadata = get_image_metadata(file_path)
    if not metadata:
        return 0
    return int(metadata.get("file_width")), int(metadata.get("file_height"))

def cmd_execute(cmd: str) -> None:
    print("CMD", cmd)
    logger.debug(f"Execute: {cmd}")
    devnull = open(os.devnull, "w")
    subprocess.call(cmd, stdout=devnull, stderr=devnull)

def is_success(file_path:str) -> bool:
    return os.path.exists(file_path) and os.stat(file_path).st_size > 0

# -------------------------
# THUMBANIL

def resize_image(
    path: str, base_height: int = 400, dest:str=None, options: str = ""
) -> str:
    _, height = oiiotool_get_size(path)

    if not dest:
        dest = get_temp_file(suffix=".jpeg")
    cmd = f'oiiotool "{path}"{options}'

    if height > base_height:
        cmd += f" -resize 0x{base_height}"

    cmd += ' --pixelaspect 1.0'
    cmd += f' -o "{dest}"'

    cmd_execute(cmd)

    if not is_success(dest):
        return None
    return dest


def compress_image(path: str, dest: str = None, options: str = "") -> str:
    if not dest:
        dest = get_temp_file(suffix=".jpeg")
    cmd = f'oiiotool "{path}"{options}'
    cmd += ' --pixelaspect 1.0'
    cmd += ' -o "{dest}"'
    cmd_execute(cmd)

    if not is_success(dest):
        return None
    return dest


def video_thumbnail(
    path: str, pre_options: list = [], options: list = [], size:int=None, dest:str=None
) -> Optional[str]:
    if not dest:
        dest = get_temp_file(suffix=".jpg")

    scale = ""
    if size:
        scale = f",scale=-1:{size}"

    command_options = ["-vframes", "1", "-vf", "thumbnail"+scale]
    command_options += options
    cmd = 'ffmpeg {pre_options} -y -i "{path}" {command_options} "{output}"'.format(
        pre_options=" ".join(pre_options),
        path=path,
        command_options=" ".join(command_options),
        output=dest,
    )

    cmd_execute(cmd)

    if not is_success(dest):
        return None
    return dest


# -------------------------
# PROXY


def create_proxy(path: str, pre_options:list=[], compression:int=150, dest:str=None):
    if not dest:
        dest = get_temp_file(suffix=".exr")
    
    pre_options = " ".join(pre_options)
    cmd = f'oiiotool {pre_options} "{path}"'
    if dest.endswith(".exr"):
        cmd += f' --compression "dwaa:{compression}"'
    cmd += f' -o "{dest}"'

    cmd_execute(cmd)

    if not is_success(dest):
        return None
    return dest

# -------------------------
# REVIEW


def create_video(
    path: str, pre_options: list = [], preset: str="web", dest: str=None
) -> str:
    if preset == "web":
        if not dest:
            dest = get_temp_file(suffix=".mp4")
        command_options = [
            "-vcodec",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "baseline",
            "-level",
            "3",
            "-vf",
            "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        ]
    else:
        if not dest:
            dest = get_temp_file(suffix=".mov")
        command_options = [
            "-vcodec",
            "dnxhd",
            "-b:v",
            "440M",
            "-vf",
            "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        ]

    cmd = 'ffmpeg {pre_options} -y -i "{path}" {command_options} "{output}"'.format(
        pre_options=" ".join(pre_options),
        path=path,
        command_options=" ".join(command_options),
        output=dest,
    )

    cmd_execute(cmd)

    if not is_success(dest):
        return None
    return dest


# -------------------------

def read_collection(sequence):
    # parse file.%04d.dpx [100-200]
    file_path, file_range = sequence.rsplit(" ", 1)
    file_start, file_end = file_range[1:-1].split("-")
    return file_path, file_start, file_end



def generate_thumb(dest, path, size=None):
    pre_options = []
    ext = os.path.splitext(path)

    if "%0" in path:
        path, file_start, file_end = read_collection(path)
        pre_options.append("-start_number")
        pre_options.append(file_start)

    if pre_options or ext not in IMAGE_EXT:
        return video_thumbnail(path, dest=dest, size=size, pre_options=pre_options)
    else:
        if size:
            return resize_image(path, dest=dest, base_height=size)
        else:
            return compress_image(path, dest=dest)


def generate_review(dest, path, preset=None):
    pre_options = []

    # TODO: add framerate (-r) option for sequence
    if "%0" in path:
        file_path, file_start, file_end = read_collection(path)
        pre_options.append("-start_number")
        pre_options.append(file_start)

    return create_video(file_path, pre_options=pre_options, dest=dest)


def generate_proxy(dest, path) -> str:
    pre_options = []
    
    if "%0" in path:
        path, file_start, file_end = read_collection(path)
        pre_options.append("--frames")
        pre_options.append(f"{file_start}-{file_end}")

    return create_proxy(path, pre_options=pre_options, dest=dest)


def add_picture(picture_type, output_id, file_path):
    with app.app_context():
        file_store.add_picture(picture_type, output_id, file_path)
        

def add_movie(movie_type, output_id, file_path):
    with app.app_context():
        file_store.add_picture(movie_type, output_id, file_path)


# -------------------------

def generate_content(output_file, output_path, dest_path, children_type):
    print("generate_content", output_path, dest_path, children_type)
    children_path = None

    # thumb
    if children_type == "thumb_high":
        dest_path += ".jpeg"
        children_path = generate_thumb(dest_path, output_path)
        if children_path:
            add_picture("original", output_file.id, children_path)
    elif children_type == "thumb_low":
        dest_path += ".jpeg"
        children_path = generate_thumb(dest_path, output_path, size=200)
        if children_path:
            add_picture("thumbnails", output_file.id, children_path)

    # review
    elif children_type == "review_high":
        dest_path += ".mov"
        children_path = generate_review(dest_path, output_path, preset="high")
    elif children_type == "review_web":
        dest_path += ".mp4"
        children_path = generate_review(dest_path, output_path, preset="web")
        if children_path:
            add_movie("previews", output_file.id, children_path)

    # proxy
    # TODO: maybe keep the same padding as the parent
    elif children_type == "proxy_exr":
        dest_path += ".%04d.exr"
        children_path = generate_proxy(dest_path, output_path)
    elif children_type == "proxy_jpeg":
        dest_path += ".%04d.jpeg"
        children_path = generate_proxy(dest_path, output_path)
    
    return children_path


@celery.task
def handle_event(data):
    print("GEN CHILDREN")
    
    children_file = ChildrenFile.get(data.get("children_file_id"))
    # file deleted or unreachable
    if not children_file:
        logger.info(f"Missing children_file: {data}")
        return

    # allow only pending status
    if children_file.file_status.name != "PENDING":
        return

    children_file.file_status = STATUS_RENDER
    children_file.save()

    # TODO: search proxy file
    children_type = children_file.output_type.name
    output_file = children_file.parent_file
    output_path = remap_path(output_file.path)

    dir_path = os.path.join(os.path.dirname(output_path), "children")
    os.makedirs(dir_path, exist_ok=True)
    dest_path = os.path.join(dir_path, f"{output_file.name}_v{output_file.revision:03d}.{children_type}")

    if not output_path:
        children_file.file_status = STATUS_FAILED
        children_file.save()
        logger.info("Nothing to generate, because output_path is empty")
        return

    try:
        children_path = generate_content(output_file, output_path, dest_path, children_type)
    except:
        logger.exception(f"Failed to generate content: {children_type}")
        children_path = None

    if not children_path:
        children_file.file_status = STATUS_FAILED
        children_file.save()
        logger.error("Failed to generate")
        return

    children_file.path = children_path.replace("\\", "/")
    children_file.file_status = STATUS_SUCCESS
    children_file.save()
