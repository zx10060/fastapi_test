"""
Settings of project from .env
"""
import functools
from typing import Optional

from pydantic import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Class for Settings of project
    """

    API_KEY: Optional[str] = None
    API_SECRET_KEY: Optional[str] = None
    API_BEARER_TOKEN: Optional[str] = None
    API_ACCESS_TOKEN: Optional[str] = None
    API_ACCESS_TOKEN_SECRET: Optional[str] = None

    MONGO_HOST: Optional[str] = None
    MONGO_PORT: Optional[int] = None

    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None

    CELERY_BROKER_HOST: Optional[str] = "localhost"
    CELERY_BROKER_PORT: Optional[str] = "6379"

    class Config:
        """
        Config file path
        """

        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings():
    """
    Return current variables from .env file as class Settings attrs
    :return: Settings
    """
    return Settings()


def with_settings(func):
    """
    Add settings to any functions
    :param func: any func
    :return: func
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        kwargs["settings"] = get_settings()
        return func(*args, **kwargs)

    return wrapped
