"""
Celery tasks for pull data from twitter
"""
import logging
from typing import Union

from celery import Celery
# from celery.schedules import crontab

from app.puller import TwitterPuller
from app.config import get_settings

log = logging.getLogger(__name__)

_config = get_settings()
_celery_broker_url = (
    f"redis://{_config.CELERY_BROKER_HOST}:{_config.CELERY_BROKER_PORT}"
)

celery = Celery(__name__)
celery.conf.broker_url = _celery_broker_url
celery.conf.result_backend = _celery_broker_url


@celery.task(name="create_task")
def create_task(self, users_list: Union[set, list]):
    """
    Start sync users from list
    :param self: For repiat celery task
    :param users_list:
    :return:
    """
    try:
        puller = TwitterPuller()
        puller.get_users_data(users_list)
    except BaseException:
        log.error("Error in task `create task` with params: %s", users_list)


@celery.task(name="start_pull_from_twitter")
def start_pull_from_twitter(self, user_id):
    """
    Pull top twitts by user_id and save to DB
    :param self: For repiat celery task
    :param user_id:
    """
    try:
        puller = TwitterPuller()
        puller.pull_data(user_id)
    except BaseException:
        log.error(
            "Error in task `start_pull_from_twitter` with params: %s",
            user_id,
        )


@celery.task(name="add_scrapper_task")
def add_scrapper_task(username):
    """
    Scrap all user twitts.
    :param username:
    """
    try:
        puller = TwitterPuller()
        puller.scrap_user_data(username)
    except BaseException:
        log.error(
            "Error in task `add_scrapper_task` with params: %s",
            username,
        )


@celery.task(name="update user`s data")
def update_user_data(self):
    """
    Update every 15 minutes user data.
    :param self: For repiat celery task
    :return:
    """
    try:
        pass
    except BaseException:
        log.error("Error in task `add_scrapper_task` with params: %s", "")
    update_user_data.retry()


# TODO add schedule for update user data from twitter
# celery.conf.beat_schedule = {
#     "trigger-email-notifications": {
#         "task": "app.update_user_data",
#         "schedule": crontab(minute="0", hour="0", day="*")
#     }
# }
