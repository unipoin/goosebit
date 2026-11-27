import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from joserfc import jwt

from goosebit.auth import create_token, get_user_from_token
from goosebit.settings import config

USERNAME = "testing@goosebit.test"


def _cookie_attributes(set_cookie: str) -> set[str]:
    # attribute names only, the token value itself must not influence the checks
    return {part.split("=")[0].strip().lower() for part in set_cookie.split(";")[1:]}


def _token(claims: dict[str, object]) -> str:
    return jwt.encode(header={"alg": "HS256"}, claims=claims, key=config.secret_key)


@pytest.mark.asyncio
async def test_login_sets_httponly_session_cookie(test_app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post("/login", data={"username": USERNAME, "password": "test"})

    assert response.status_code == 200
    # the token is still returned for API clients
    assert "access_token" in response.json()

    cookie = response.headers["set-cookie"]
    attributes = _cookie_attributes(cookie)
    assert cookie.startswith("session_id=")
    assert "httponly" in attributes
    assert "samesite=lax" in cookie.lower()
    assert f"max-age={config.session_lifetime}" in cookie.lower()
    # plain http request without explicit config: no Secure flag, otherwise the cookie would be dropped
    assert "secure" not in attributes


@pytest.mark.asyncio
async def test_login_cookie_secure_flag_configurable(test_app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "session_cookie_secure", True)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post("/login", data={"username": USERNAME, "password": "test"})

    assert response.status_code == 200
    assert "secure" in _cookie_attributes(response.headers["set-cookie"])


@pytest.mark.asyncio
async def test_token_valid(test_app: FastAPI) -> None:
    user = await get_user_from_token(create_token(USERNAME))
    assert user is not None
    assert user.username == USERNAME


@pytest.mark.asyncio
async def test_token_expired_rejected(test_app: FastAPI) -> None:
    now = int(time.time())
    token = _token({"username": USERNAME, "iat": now - 120, "exp": now - 60})
    assert await get_user_from_token(token) is None


@pytest.mark.asyncio
async def test_token_without_expiry_rejected(test_app: FastAPI) -> None:
    # tokens issued by older versions never expired and must not be accepted anymore
    assert await get_user_from_token(_token({"username": USERNAME})) is None


@pytest.mark.asyncio
async def test_token_malformed_rejected(test_app: FastAPI) -> None:
    assert await get_user_from_token("not-a-token") is None


@pytest.mark.asyncio
async def test_expired_token_cannot_access_api(test_app: FastAPI) -> None:
    now = int(time.time())
    token = _token({"username": USERNAME, "iat": now - 120, "exp": now - 60})

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/api/v1/devices", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
