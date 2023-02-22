import functools
from typing import Optional

from pydantic import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Class for Settings of project
    """

    API_KEY: Optional[str]
    API_SECRET_KEY: Optional[str]
    API_BEARER_TOKEN: Optional[str]
    API_ACCESS_TOKEN: Optional[str]
    API_ACCESS_TOKEN_SECRET: Optional[str]

    MONGO_HOST: Optional[str]
    MONGO_PORT: Optional[int]

    REDIS_HOST: Optional[str]
    REDIS_PORT: Optional[int]

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
