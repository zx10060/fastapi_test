"""
File for test controller
"""
import json
import pytest
from app import services
from app.models import InternalError, Account, ProfilesList, Session
from httpx import AsyncClient

_data = {
    "profiles": [
        "https://twitter.com/test",
        "test",
        "https://twitter.com/test//",
        "test///",
    ]
}


async def mock_internal_error(*args, **kwargs):
    """
    Function for raise InternalError
    """
    raise InternalError


async def mock_none(*args, **kwargs):
    """
    Function for return None
    """
    return None


@pytest.mark.anyio
async def test_add_profiles(monkeypatch, client: AsyncClient):
    """
    Good response test
    """

    async def mock_create_new_task(data=None):
        return Session.construct(session_id="12341234")

    monkeypatch.setattr(services, "create_new_task", mock_create_new_task)

    response = await client.post("/api/users", json=_data)

    assert response.status_code == 200
    assert response.json() == {"session_id": "12341234"}


@pytest.mark.anyio
async def test_add_profiles_internal_error(monkeypatch, client: AsyncClient):
    """
    Sever error test.
    """

    monkeypatch.setattr(services, "create_new_task", mock_internal_error)
    response = await client.post("/api/users", json=_data)

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal error, try leter."}


@pytest.mark.anyio
async def test_add_profiles_bad_response(monkeypatch, client: AsyncClient):
    """
    Bad response test.
    """

    monkeypatch.setattr(services, "create_new_task", mock_none)
    response = await client.post("/api/users", json=_data)

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Some error with add new task, please try leter."
    }


@pytest.mark.anyio
async def test_get_status(monkeypatch, client: AsyncClient):
    async def mock_get_status_by_session(data=None):
        from app.models import AccountStatus

        return [
            AccountStatus(username="test", status="ok"),
            AccountStatus(username="test", status="ok"),
        ]

    monkeypatch.setattr(services, "get_status_by_session", mock_get_status_by_session)

    session_id = "235434132"
    response = await client.get(f"/api/users/status?session_id={session_id}")

    assert response.status_code == 200
    assert response.json() == [
        {"username": "test", "status": "ok"},
        {"username": "test", "status": "ok"},
    ]


@pytest.mark.anyio
async def test_get_status_bad_response(monkeypatch, client: AsyncClient):
    response = await client.get(f"/api/users/status?session_id=")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Bad response, request dosnt contain key session_id"
    }


@pytest.mark.anyio
async def test_get_status_empty_response(monkeypatch, client: AsyncClient):
    monkeypatch.setattr(services, "get_status_by_session", mock_none)

    session_id = "235434132"
    response = await client.get(f"/api/users/status?session_id={session_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Session_id key not valid"}


@pytest.mark.anyio
async def test_get_status_internal_error(monkeypatch, client: AsyncClient):
    monkeypatch.setattr(services, "get_status_by_session", mock_internal_error)

    session_id = "235434132"
    response = await client.get(f"/api/users/status?session_id={session_id}")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal error, try leter."}


@pytest.mark.anyio
async def test_get_user_data(monkeypatch, client: AsyncClient):
    async def mock_get_user_data_by_username(_username):
        return Account.construct(
            id="63c251447c36683bae7dadca",
            twitter_id="test",
            name="test",
            username=_username,
            following_count=111,
            followers_count=111,
            description="test",
            status="OK",
        )

    monkeypatch.setattr(
        services, "get_user_data_by_username", mock_get_user_data_by_username
    )
    username = "test"
    response = await client.get(f"/api/user/{username}")

    assert response.status_code == 200
    assert response.json() == {
        "_id": "63c251447c36683bae7dadca",
        "twitter_id": "test",
        "name": "test",
        "username": username,
        "following_count": 111,
        "followers_count": 111,
        "description": "test",
        "status": "OK",
    }


@pytest.mark.anyio
async def test_get_user_data_notfound(monkeypatch, client: AsyncClient):
    monkeypatch.setattr(services, "get_user_data_by_username", mock_none)

    response = await client.get(f"/api/user/test")

    assert response.status_code == 404
    assert response.json() == {"detail": "User name not found in DB."}


@pytest.mark.anyio
async def test_get_user_data_error(monkeypatch, client: AsyncClient):
    monkeypatch.setattr(services, "get_user_data_by_username", mock_internal_error)

    response = await client.get(f"/api/user/test")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal error, try leter."}


@pytest.mark.anyio
async def test_get_twitts_ok(monkeypatch, client: AsyncClient):
    async def mock_get_last_ten_twitts_by_twitter_id(twitter_id):
        assert twitter_id == "test"
        return [
            "test",
            "test",
        ]

    monkeypatch.setattr(
        services,
        "get_last_ten_twitts_by_twitter_id",
        mock_get_last_ten_twitts_by_twitter_id,
    )

    response = await client.get(f"/api/twitts/test")

    assert response.status_code == 200
    assert response.json() == [
        "test",
        "test",
    ]


@pytest.mark.anyio
async def test_get_twitts_notfound(monkeypatch, client: AsyncClient):
    monkeypatch.setattr(
        services,
        "get_last_ten_twitts_by_twitter_id",
        mock_none,
    )

    response = await client.get(f"/api/twitts/test")

    assert response.status_code == 404
    assert response.json() == {"detail": "Twitter id not found in DB."}


@pytest.mark.anyio
async def test_get_twitts_error(monkeypatch, client: AsyncClient):
    monkeypatch.setattr(
        services,
        "get_last_ten_twitts_by_twitter_id",
        mock_internal_error,
    )

    response = await client.get(f"/api/twitts/test")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal error, try leter."}
