"""
Service layer for app
"""
import logging
import re
from typing import Union, Optional

from fastapi.encoders import jsonable_encoder

from app import database, celery_twitter
from app.models import (
    Account,
    AccountStatus,
    SyncTask,
    InternalError,
    Session,
    ProfilesList,
)

log = logging.getLogger(__name__)


TWITTER_USERNAME_REGEX = re.compile(r"^(?!.*\.\.)(?!.*\.$)[^\W][\w.]{0,15}$")


async def get_status_by_session(
    session_id: str,
) -> Union[list[AccountStatus], None]:
    """
    Return
    :param session_id: str of Session ID(Task ID)
    :return:
    """
    # load from Mongo by session_id
    query = {"_id": {"$eq": session_id}}

    task = await database.a_db.tasks.find_one(query)
    if not task:
        return []
    try:
        # find all account from task
        query = {"username": {"$in": task["users_list"]}}
        accounts = database.a_db.accounts.find(query)
        return [account async for account in accounts]
    except BaseException:
        raise InternalError


async def get_user_data_by_username(username: str) -> Union[Account, None]:
    """
    Load user data from DB

    :param username:
    :return:
    """
    query = {"username": {"$eq": username}}
    try:
        account = await database.a_db.accounts.find_one(query)
        if account:
            return account
    except BaseException:
        raise InternalError


async def get_last_ten_twitts_by_twitter_id(
    twitter_id: str,
) -> list[Optional[str]]:
    """
    Return 10 last twitts by twitter id
    :param twitter_id:
    :return:
    """
    try:
        cursor = database.a_db_data[twitter_id].find()
        return [twitt["text"] for twitt in await cursor.to_list(length=10)]
    except BaseException:
        raise InternalError


def _get_username(value: str) -> Optional[str]:
    """
    Return username from url or return None
    :param value: url or username
    :return:
    """
    if isinstance(value, str):
        match = re.match(r"(?:https?://)?(?:www\.)?twitter\.com/(\w+)/?", value)
        if match:
            username = match.group(1)
            if TWITTER_USERNAME_REGEX.match(username):
                return username
    return None


async def create_new_task(data: ProfilesList) -> Union[Session, None]:
    """
    Create new task and return dict like:
        {
            'session_id': 'kjg234kj1243kj21h3k12'
        }
    :param data:
    :return:
    """
    try:
        # parse str of urls and names to usernames
        users_set = {_get_username(item) for item in data.profiles if item}
        if not users_set:
            return None

        # create new task entity
        new_task = SyncTask(users_list=users_set)

        # save new task to mongo
        task = await database.a_db.tasks.insert_one(jsonable_encoder(new_task))
        log.info("Create new task in mongo: %s.", task.inserted_id)

        # create new task in celery
        celery_task_id = celery_twitter.create_task.delay(users_set)
        log.info("Create new task in celery: %s", celery_task_id)

        # return task id
        return Session(session_id=task.inserted_id)

    except BaseException:
        raise InternalError
