import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from goosebit.db.models import User


@pytest.mark.asyncio
async def test_setup_post_rejected_when_user_exists(test_app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post("/setup", data={"username": "attacker@example.com", "password": "pwned"})

    # an existing installation must not allow creating another admin via setup
    assert response.status_code == 302
    assert response.headers["location"].endswith("/login")
    assert await User.get_or_none(username="attacker@example.com") is None


@pytest.mark.asyncio
async def test_setup_get_redirects_when_user_exists(test_app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/setup")

    assert response.status_code == 302
    assert response.headers["location"].endswith("/login")


@pytest.mark.asyncio
async def test_setup_post_allowed_without_users(test_app: FastAPI) -> None:
    await User.all().delete()

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post("/setup", data={"username": "admin@example.com", "password": "secret"})

    assert response.status_code == 200
    assert "access_token" in response.json()
    user = await User.get(username="admin@example.com")
    assert user.permissions == ["*"]
