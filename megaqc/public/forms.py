# -*- coding: utf-8 -*-
"""
Public forms using Pydantic for validation.
"""
from typing import Optional

from pydantic import BaseModel, field_validator


class LoginForm(BaseModel):
    """
    Login form schema.
    """

    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Username is required")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Password is required")
        return v


class LoginResponse(BaseModel):
    """Response model for login."""

    success: bool
    message: str
    redirect_url: Optional[str] = None
