from __future__ import annotations

import logging
import time
from typing import Annotated, Iterable

from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.requests import HTTPConnection, Request
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from joserfc import jwt
from joserfc.errors import JoseError

from goosebit.db.models import User
from goosebit.settings import PWD_CXT, config  # type: ignore[attr-defined]
from goosebit.users import UserManager

logger = logging.getLogger(__name__)


SESSION_COOKIE = "session_id"
TOKEN_ALGORITHM = "HS256"

# tokens without expiry (issued by older versions) are rejected
_claims_registry = jwt.JWTClaimsRegistry(exp={"essential": True}, iat={"essential": True})


oauth2_bearer = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)


async def oauth2_auth(request: Request) -> str | None:
    return await oauth2_bearer(request)


async def session_auth(connection: HTTPConnection) -> str | None:
    return connection.cookies.get(SESSION_COOKIE)


def create_token(username: str) -> str:
    now = int(time.time())
    claims = {"username": username, "iat": now, "exp": now + config.session_lifetime}
    return jwt.encode(header={"alg": TOKEN_ALGORITHM}, claims=claims, key=config.secret_key)


async def get_user_from_token(token: str | None) -> User | None:
    if token is None:
        return None
    try:
        token_data = jwt.decode(token, config.secret_key, algorithms=[TOKEN_ALGORITHM])
        _claims_registry.validate(token_data.claims)
        username = token_data.claims["username"]
        return await UserManager.get_user(username)
    except (JoseError, LookupError, ValueError):
        return None


def set_session_cookie(request: Request, response: Response, token: str) -> None:
    # set by the server so the token is not readable by JavaScript (HttpOnly)
    secure = config.session_cookie_secure
    if secure is None:
        secure = request.url.scheme == "https"
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=config.session_lifetime,
        path="/",
        secure=secure,
        httponly=True,
        samesite="lax",
    )


async def login_user(username: str, password: str) -> str:
    user = await UserManager.get_user(username)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.enabled:
        raise HTTPException(
            status_code=401,
            detail="User has been disabled, please contact your administrator",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        PWD_CXT.verify(user.hashed_pwd, password)
    except VerifyMismatchError:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return create_token(user.username)


async def get_current_user(
    session_token: Annotated[str | None, Depends(session_auth)] = None,
    oauth2_token: Annotated[str | None, Depends(oauth2_auth)] = None,
) -> User | None:
    session_user = await get_user_from_token(session_token)
    oauth2_user = await get_user_from_token(oauth2_token)
    user = session_user or oauth2_user
    return user


async def get_user_from_request(request: Request) -> User | None:
    token = await session_auth(request) or await oauth2_auth(request)
    return await get_user_from_token(token)


async def redirect_if_unauthenticated(
    connection: HTTPConnection, user: Annotated[User, Depends(get_current_user)]
) -> None:
    if user is None:
        raise HTTPException(
            status_code=302,
            headers={"location": str(connection.url_for("login_get"))},
            detail="Invalid username",
        )
    if not user.enabled:
        raise HTTPException(
            status_code=302,
            headers={"location": str(connection.url_for("login_get"))},
            detail="Disabled user",
        )


async def redirect_if_authenticated(
    connection: HTTPConnection, user: Annotated[User, Depends(get_current_user)]
) -> None:
    if user is not None:
        if not user.enabled:
            return
        raise HTTPException(
            status_code=302,
            headers={"location": str(connection.url_for("ui_root"))},
            detail="Already logged in",
        )
    if await User.all().count() == 0:
        raise HTTPException(
            status_code=302,
            headers={"location": str(connection.url_for("setup_get"))},
            detail="No users set up",
        )


async def redirect_if_users_exist(connection: HTTPConnection) -> None:
    if await User.all().count() > 0:
        raise HTTPException(
            status_code=302,
            headers={"location": str(connection.url_for("login_get"))},
            detail="An admin user already exists",
        )


async def validate_current_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.enabled:
        raise HTTPException(
            status_code=401,
            detail="Disabled user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def validate_user_permissions(
    connection: HTTPConnection,
    security: SecurityScopes,
    user: User = Depends(get_current_user),
) -> HTTPConnection:
    if not check_permissions(security.scopes, user.permissions):
        logger.warning(f"{user.username} does not have sufficient permissions")
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return connection


def check_permissions(scopes: Iterable[str] | None, permissions: Iterable[str]) -> bool:
    deny_permissions = [p.lstrip("!") for p in permissions if p.startswith("!")]
    allow_permissions = [p for p in permissions if not p.startswith("!")]
    if scopes is None:
        return True
    for scope in scopes:
        if any([_check_permission(scope, permission) for permission in deny_permissions]):
            return False
        if not any([_check_permission(scope, permission) for permission in allow_permissions]):
            return False
    return True


def _check_permission(scope: str, permission: str) -> bool:
    split_scope = scope.split(".")
    for idx, permission in enumerate(permission.split(".")):
        if permission == "*":
            continue
        if not split_scope[idx] == permission:
            return False
    return True
