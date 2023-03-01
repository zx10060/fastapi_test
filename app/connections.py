"""
File for twitter connection.
"""

import logging
from celery import Celery
import tweepy

from app.config import get_settings


log = logging.getLogger()

settings = get_settings()

try:
    auth = tweepy.OAuthHandler(settings.API_KEY, settings.API_SECRET_KEY)
    auth.set_access_token(settings.API_ACCESS_TOKEN, settings.API_ACCESS_TOKEN_SECRET)
    _connection_to_twitter = tweepy.API(auth, wait_on_rate_limit=True)
except BaseException:
    log.error("Some error with twitter connection..")


def get_api():
    """
    Return twitter coccection.
    :return:
    """
    return _connection_to_twitter


try:
    _celery_broker_url = (
        f"redis://{settings.CELERY_BROKER_HOST}:{settings.CELERY_BROKER_PORT}"
    )
    _celery = Celery(__name__)
    _celery.conf.broker_url = _celery_broker_url
    _celery.conf.result_backend = _celery_broker_url
except BaseException:
    log.error("Error connection to redis!")


def get_celery():
    """
    Return celery app.
    :return:
    """
    return _celery
