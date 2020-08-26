import redis
import sys

from celery import Celery
from zou.app import config


celery = Celery('zou', broker='redis://{}:{}/{}'.format(
    config.KEY_VALUE_STORE["host"],
    config.KEY_VALUE_STORE["port"],
    config.KV_JOB_DB_INDEX
))


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # get task
    import zou.plugins.event_handlers

    # get periodic task
    from zou.plugins.event_periodic import muster_jobs

    print("add periodic task")
    sender.add_periodic_task(60.0, muster_jobs.handle_event.s(), name="muster_jobs")