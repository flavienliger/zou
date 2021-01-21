# Not used - it exists only for an example
from zou.app.events import celery
from zou.app.services.playlists_service import build_playlist_job
from zou.app.utils import emails, chats

# Celery tasks

@celery.task
def build_playlist_task(playlist, email):
    build_playlist_job(playlist, email)

@celery.task
def send_email_task(subject, message, email):
    emails.send_email(subject, message, email)

@celery.task
def send_to_slack_task(token, user, message):
    chats.send_to_slack(token, user, message)

event_map = {}