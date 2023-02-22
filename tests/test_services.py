"""
Fiile for test functions
"""
import pytest

from app import database, celery_twitter
from app.services import (
    get_status_by_session,
    get_last_ten_twitts_by_twitter_id,
    create_new_task,
)
from app.database import sync_client, async_client
from app.models import InternalError, ProfilesList

TEST_DATABASE = "test"
TEST_TASK = {"users_list": ["test"]}

TEST_ACCOUNT = {
    "twitter_id": "test",
    "name": "test",
    "username": "test",
    "following_count": 111,
    "followers_count": 111,
    "description": "test",
    "status": "test",
}
FAKE_TASK = ["http://twitter.com/test"]
TEST_TWITT = {"text": "its test twitt"}

db = sync_client[TEST_DATABASE]
a_db = async_client[TEST_DATABASE]


def insert_fake_data():
    db.accounts.insert_one(TEST_ACCOUNT)
    db.twitts.insert_one(TEST_TWITT)
    task = db.tasks.insert_one(TEST_TASK)
    return task.inserted_id


def delete_fake_data():
    db.accounts.drop()
    db.tasks.drop()
    db.twitts.drop()
    sync_client.drop_database(TEST_DATABASE)


@pytest.fixture
def fake_data():
    session_id = insert_fake_data()
    yield session_id
    delete_fake_data()


@pytest.mark.anyio
async def test_get_status_by_session(fake_data, monkeypatch):
    monkeypatch.setattr(database, "a_db", a_db)
    result = await get_status_by_session(fake_data)
    assert result[-1] == TEST_ACCOUNT


@pytest.mark.anyio
async def test_get_status_by_session_empty_response(fake_data, monkeypatch):
    monkeypatch.setattr(database, "a_db", a_db)
    _session_id = "000"
    result = await get_status_by_session(_session_id)
    assert result == []


@pytest.mark.anyio
async def test_get_status_by_session_rise_error(fake_data, monkeypatch):
    _filter = {"_id": fake_data}
    db.tasks.update_one(_filter, {"$set": {"users_list": 25}})
    monkeypatch.setattr(database, "a_db", a_db)
    try:
        result = await get_status_by_session(fake_data)
    except InternalError:
        assert 0 == 0


from app.services import get_user_data_by_username


@pytest.mark.anyio
async def test_get_userdata_by_username(fake_data, monkeypatch):
    monkeypatch.setattr(database, "a_db", a_db)
    result = await get_user_data_by_username(TEST_ACCOUNT["username"])
    assert result == TEST_ACCOUNT


@pytest.mark.anyio
async def test_get_userdata_by_username_notfound(fake_data, monkeypatch):
    monkeypatch.setattr(database, "a_db", a_db)
    result = await get_user_data_by_username("not_found")
    assert result == None


@pytest.mark.anyio
async def test_get_userdata_by_username_internal_error(fake_data, monkeypatch):
    monkeypatch.setattr(database, "a_db", a_db)
    db.accounts.drop()
    try:
        result = await get_user_data_by_username(TEST_ACCOUNT["username"])
    except InternalError:
        assert 0 == 0


@pytest.mark.anyio
async def test_get_last_ten_twitts_by_twitter_id(fake_data, monkeypatch):
    monkeypatch.setattr(database, "a_db_data", a_db)

    _twitter_id = TEST_ACCOUNT["twitter_id"]
    result = await get_last_ten_twitts_by_twitter_id(_twitter_id)
    for _twitt in result:
        assert result["text"] == TEST_TWITT["text"]


@pytest.mark.anyio
async def test_get_last_ten_twitts_by_twitter_id(fake_data, monkeypatch):
    monkeypatch.setattr(database, "a_db_data", a_db)
    result = await get_last_ten_twitts_by_twitter_id("not_found")
    assert result == []


@pytest.mark.anyio
async def test_get_last_ten_twitts_by_twitter_id_internal_error(
    fake_data,
    monkeypatch,
):
    monkeypatch.setattr(database, "a_db_data", a_db)
    try:
        # collection not found
        result = await get_last_ten_twitts_by_twitter_id("twitter_id")
        # or any internal error
    except InternalError:
        assert 0 == 0


class fake_create_task:
    """
    Mock for Celery tasks.
    """

    @staticmethod
    def delay(*args, **kwargs):
        return True


@pytest.mark.anyio
async def test_create_new_task(monkeypatch):
    monkeypatch.setattr(database, "a_db", a_db)
    monkeypatch.setattr(celery_twitter, "create_task", fake_create_task)
    result = await create_new_task(ProfilesList.construct(profiles=FAKE_TASK))
    _session_id = db.tasks.find_one({"users_list": ["test"]})["_id"]
    delete_fake_data()
    assert result.dict() == {"session_id": _session_id}


@pytest.mark.anyio
async def test_create_new_task_badrequest(monkeypatch):
    monkeypatch.setattr(database, "a_db", a_db)
    monkeypatch.setattr(celery_twitter, "create_task", fake_create_task)
    result = await create_new_task(ProfilesList.construct(profiles=[""]))
    delete_fake_data()
    assert result is None


@pytest.mark.anyio
async def test_create_new_task_error(monkeypatch):
    monkeypatch.setattr(database, "a_db", a_db)
    monkeypatch.setattr(celery_twitter, "create_task", fake_create_task)
    delete_fake_data()
    try:
        await create_new_task(FAKE_TASK)
    except InternalError:
        assert 0 == 0
    finally:
        db.tasks.drop()
