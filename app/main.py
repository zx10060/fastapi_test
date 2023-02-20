"""
Test api for scrapping twitter accounts
"""
import logging
import uvicorn

from fastapi import FastAPI, HTTPException, Body


from app.models import AccountStatus, InternalError, Session, ProfilesList, Account
from app import services


log = logging.getLogger(__name__)

description = """
Test API for scrapping twitter data by scrapper or (and) with using account app. 🚀

## Users

You can **read items**.

## Users

You will be able to:

* **Create users** (_not implemented_).
* **Read users** (_not implemented_).
"""

app = FastAPI(
    title="TestAPI for twitter scrapping",
    description=description,
    version="0.0.1",
    terms_of_service="http://example.com/terms/",
    contact={
        "name": "Stephan",
        "email": "zz.zx100@mail.ru",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)


@app.post(
    "/api/users",
    response_description="Add new task for sync from twitter",
    response_model=Session,
)
async def add_profiles(data: ProfilesList = Body(...)):
    """
    Add list of links to users in twitter
    Examples:
    {
        "profiles": [
            "https://twitter.com/username",
            "username",
            "https://twitter.com/username/",
        ]
    }
    """
    try:
        result = await services.create_new_task(data)
        if result:
            return result
        else:
            raise HTTPException(
                status_code=500,
                detail="Some error with add new task, please try leter.",
            )
    except InternalError:
        raise HTTPException(status_code=500, detail="Internal error, try leter.")


@app.get(
    "/api/users/status",
    response_description="List with status for sync",
    response_model=list[AccountStatus],
)
async def get_status(session_id: str):
    """
    Return list of dict with status of parsing accounts by session_id
    """
    try:
        if not session_id:
            raise HTTPException(
                status_code=404,
                detail="Bad response, request dosnt contain key session_id",
            )

        status_list = await services.get_status_by_session(session_id)
        if status_list:
            return status_list
        else:
            raise HTTPException(status_code=404, detail="Session_id key not valid")
    except InternalError:
        raise HTTPException(status_code=500, detail="Internal error, try leter.")


@app.get(
    "/api/user/{username}",
    response_model=Account,
)
async def get_user_data(username: str):
    """
    Return Twitter account data from DB only.
    :param username: str
    :return: dict
    """
    try:
        account = await services.get_user_data_by_username(username)
        if account:
            return account
        else:
            raise HTTPException(status_code=404, detail="User name not found in DB.")
    except InternalError:
        raise HTTPException(status_code=500, detail="Internal error, try leter.")


@app.get(
    "/api/twitts/{twitter_id}",
    response_description="List last 10 twitts of user",
    response_model=list[str],
)
async def get_twitts(twitter_id: str):
    """
    Get last 10 twitts by twitter_id from DB only.
    :param twitter_id:
    :return:
    """
    try:
        twitts = await services.get_last_ten_twitts_by_twitter_id(twitter_id)
        if twitts:
            return twitts
        else:
            raise HTTPException(status_code=404, detail="Twitter id not found in DB.")
    except InternalError:
        raise HTTPException(status_code=500, detail="Internal error, try leter.")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0")
