# -*- coding: utf-8 -*-
"""
Authentication module for FastAPI.

Provides session-based authentication and API token authentication.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.hash import argon2
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from megaqc.database import get_async_session
from megaqc.settings import Settings

# Security schemes
api_key_header = APIKeyHeader(name="access_token", auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token", auto_error=False)

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, settings: Settings, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str, salt: str) -> bool:
    """Verify a password against a hash."""
    return argon2.verify(plain_password + salt, hashed_password)


async def get_user_by_token(
    session: AsyncSession,
    token: str,
) -> Optional["User"]:
    """Get user by API token."""
    from megaqc.user.models import User

    result = await session.execute(
        select(User).where(User.api_token == token)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> Optional["User"]:
    """Get user by ID."""
    from megaqc.user.models import User

    result = await session.execute(
        select(User).where(User.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    api_token: Optional[str] = Depends(api_key_header),
    session_token: Optional[str] = Cookie(None, alias="session_token"),
) -> Optional["User"]:
    """
    Get the current user from either API token or session.

    Returns None if not authenticated (for optional auth).
    """
    from megaqc.user.models import User

    # Try API token first
    if api_token:
        user = await get_user_by_token(session, api_token)
        if user and user.active:
            return user

    # Try session token (JWT)
    if session_token:
        try:
            settings = request.state.settings
            payload = jwt.decode(session_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            user_id: int = payload.get("sub")
            if user_id is not None:
                user = await get_user_by_id(session, user_id)
                if user and user.active:
                    return user
        except JWTError:
            pass

    return None


async def get_current_active_user(
    current_user: Optional["User"] = Depends(get_current_user),
) -> "User":
    """
    Get the current active user. Raises 401 if not authenticated.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not current_user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_admin_user(
    current_user: "User" = Depends(get_current_active_user),
) -> "User":
    """
    Get the current admin user. Raises 403 if not admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def login_required(func):
    """Decorator for routes that require authentication."""
    async def wrapper(*args, current_user: "User" = Depends(get_current_active_user), **kwargs):
        return await func(*args, current_user=current_user, **kwargs)
    return wrapper


def admin_required(func):
    """Decorator for routes that require admin access."""
    async def wrapper(*args, current_user: "User" = Depends(get_current_admin_user), **kwargs):
        return await func(*args, current_user=current_user, **kwargs)
    return wrapper

