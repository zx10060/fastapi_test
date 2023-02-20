"""
Service layer for app
"""
import logging
from typing import Union
from app import database, celery_twitter
from fastapi.encoders import jsonable_encoder
from app.models import (
    Account,
    AccountStatus,
    SyncTask,
    InternalError,
    Session,
    ProfilesList,
)

log = logging.getLogger(__name__)


async def get_status_by_session(session_id: str) -> Union[list[AccountStatus], None]:
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
        return [account async for account in database.a_db.accounts.find(query)]
    except:
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
    except:
        raise InternalError


async def get_last_ten_twitts_by_twitter_id(twitter_id: str) -> list[Union[str, None]]:
    """
    Return 10 last twitts by twitter id
    :param twitter_id:
    :return:
    """
    try:
        cursor = database.a_db_data[twitter_id].find()
        return [twitt["text"] for twitt in await cursor.to_list(length=10)]
    except:
        raise InternalError


def _get_username(value: str) -> str:
    """
    Return username from url or return str
    :param value: url or username
    :return:
    """
    if isinstance(value, str):
        _data = value.split("/")
        if len(_data) == 1 and value:
            return value
        else:
            while _data[-1] == "":
                _data.pop()
            return _data[-1]


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
        users_list = {_get_username(item) for item in data.profiles if item}
        if not users_list:
            return None

        # create new task entity
        new_task = SyncTask(users_list=users_list)

        # save new task to mongo
        task = await database.a_db.tasks.insert_one(jsonable_encoder(new_task))
        log.info("Create new task in mongo: %s.", task.inserted_id)

        # create new task in celery
        celery_task_id = celery_twitter.create_task.delay(users_list)
        log.info("Create new task in celery: %s", celery_task_id)

        # return task id
        return Session(session_id=task.inserted_id)

    except:
        raise InternalError
