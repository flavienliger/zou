# Not used - it exists only for an example
import redis
import sys

from celery import Celery
from zou.app import config


celery = Celery('zou', broker='redis://{}:{}/{}'.format(
    config.KEY_VALUE_STORE["host"],
    config.KEY_VALUE_STORE["port"],
    config.KV_JOB_DB_INDEX
))

import event_handlers