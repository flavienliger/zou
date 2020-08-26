import os
import clique
import logging

from zou.app.models.output_file import OutputFile
from zou.app.models.children_file import ChildrenFile
from zou.app.models.file_status import FileStatus
from zou.app.utils.dd import remap_path
from zou.app.celery import celery

from zou.plugins.event_handlers import output_file_new, generate_children
from . import zou_muster_custom as muster_custom

logger = logging.getLogger(__name__)
MUSTER_ACCOUNT = {
    "login": "admin",
    "password": "Lt1Khac=",
}


def get_job_status(muster_session, job_id):
    try:
        job_chunks = muster_session.get_chunks_by_jobid(job_id)
    except:
        logger.exception("Failed to get chunk of job {0}".format(job_id))
        return None, None

    # job removed
    if not job_chunks:
        return "removed", None

    progress = 0

    for item in job_chunks:
        if item["status"] in ["COMPLETED", "WARNING", "ERROR"]:
            progress += 1
        elif item["requeued"] >= 10:
            return "failed", 0
    
    if progress == job_chunks.__len__():
        return "completed", 100
    else:
        return "inprogress", round(progress/job_chunks.__len__()*100)


def check_completed(file_path):
    if "%" in file_path:
        collection = clique.parse(file_path)
        for element in collection:
            print("element", element)
            if not os.path.exists(element) or os.stat(element).st_size <= 0:
                return False
        return True
    else:
        return os.path.exists(file_path) and os.stat(file_path).st_size > 0
    

def render_completed(element):
    # OutputFile
    if element.__class__.__name__ == "OutputFile":
        element.file_status_id = FileStatus.get_by(name="WAITING").id
        element.save()
        output_file_new.handle_event.delay({"output_file_id": element.id})
    # ChildrenFile
    else:
        element.file_status_id = FileStatus.get_by(name="GENERATED").id
        element.save()
        generate_children.handle_event.delay({"children_file_id": element.id})


def render_progress(element, progression):
    data = {"render_progress": progression}
    if element.data:
        # ignore same progress
        if element.get("render_progress") == progression:
            return

        data.update(element.data)

    element.data = data
    element.save()


def render_failed(element):
    element.file_status_id = FileStatus.get_by(name="RENDER FAILED").id
    element.save()


def check_files(muster_session, data):
    for element in data:
        _, muster_job_id = element.render_info.split(":")
        job_status, progression = get_job_status(muster_session, muster_job_id)

        # error api
        if not job_status:
            continue

        print("JOB STATUS", job_status)
        # completed
        if job_status == "completed":
            if not check_completed(remap_path(element.path)):
                job_status = "failed"
            else:
                render_completed(element)

        # update progress
        elif job_status == "inprogress":
            render_progress(element, progression)
            
        # failed
        if job_status in ["removed", "failed"]:
            render_failed(element)


@celery.task
def handle_event():
    print("muster_jobs")
        
    muster_session = muster_custom.MusterManager(
        MUSTER_ACCOUNT["login"], MUSTER_ACCOUNT["password"]
    )
    
    # ignore connection failed
    if muster_session.login():
        return
    
    # OutputFile
    status = FileStatus.get_by(name="IN RENDER")
    data_output_file = OutputFile.query.filter(
        OutputFile.render_info.like("MUSTER%")
    ).filter_by(file_status_id=status.id).all()

    # ChildrenFile
    status = FileStatus.get_by(name="IN RENDER")
    data_children_file = ChildrenFile.query.filter(
        ChildrenFile.render_info.like("MUSTER%")
    ).filter_by(file_status_id=status.id).all()

    check_files(muster_session, data_output_file)
    check_files(muster_session, data_children_file)