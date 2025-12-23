import os
from enum import IntEnum, auto
from functools import wraps
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from megaqc.settings import get_settings
from megaqc.user.models import User


def get_upload_dir() -> str:
    """Get the upload directory, creating it if necessary."""
    settings = get_settings()
    upload_dir = settings.UPLOAD_FOLDER
    if not os.path.isdir(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def get_unique_filename() -> str:
    """Generate a unique filename in the upload directory."""
    upload_dir = get_upload_dir()
    while True:
        proposed = os.path.join(upload_dir, str(uuid4()))
        if not os.path.exists(proposed):
            return proposed


class Permission(IntEnum):
    """Permission levels for API access."""
    NONUSER = auto()
    USER = auto()
    ADMIN = auto()


async def get_user_from_token(
    session: AsyncSession, access_token: Optional[str]
) -> tuple[Optional[User], Permission, Optional[str]]:
    """
    Get user and permission level from access token.

    Returns:
        Tuple of (user, permission_level, error_message)
    """
    if not access_token:
        return None, Permission.NONUSER, "No access token provided. Please add a header with the name 'access_token'."

    result = await session.execute(
        select(User).where(User.api_token == access_token)
    )
    user = result.scalar_one_or_none()

    if not user:
        return None, Permission.NONUSER, "The provided access token was invalid."

    if hasattr(user, "is_anonymous") and user.is_anonymous:
        return user, Permission.NONUSER, None

    if user.is_admin:
        return user, Permission.ADMIN, None

    if not user.active:
        return user, Permission.NONUSER, "User is not active."

    return user, Permission.USER, None


def check_permission(
    permission: Permission,
    min_level: Permission,
    error_detail: Optional[str] = None
) -> None:
    """
    Check if the permission level meets the minimum requirement.

    Raises HTTPException if permission is insufficient.
    """
    if permission < min_level:
        detail = error_detail or "Insufficient permissions to access this resource"
        raise HTTPException(status_code=403, detail=detail)
