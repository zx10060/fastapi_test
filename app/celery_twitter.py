"""
Celery tasks for pull data from twitter
"""
import logging
import os
from typing import Union

from celery import Celery
from app.puller import TwitterPuller

log = logging.getLogger(__name__)
celery = Celery(__name__)
celery.conf.broker_url = os.environ.get(
    "CELERY_BROKER_URL",
    "redis://localhost:6379",
)
celery.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND",
    "redis://localhost:6379",
)


@celery.task(name="create_task")
def create_task(self, users_list: Union[set, list]):
    """
    Start sync users from list
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
    :return:
    """
    try:
        pass
    except BaseException:
        log.error("Error in task `add_scrapper_task` with params: %s", "")
    update_user_data.retry()
