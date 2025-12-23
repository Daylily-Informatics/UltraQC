# -*- coding: utf-8 -*-
"""
User forms using Pydantic for validation.
"""
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator


class AdminForm(BaseModel):
    """Admin user edit form schema."""

    user_id: Optional[int] = None
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    active: bool = False
    is_admin: bool = False

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or len(v) < 3 or len(v) > 25:
            raise ValueError("Username must be between 3 and 25 characters")
        return v.strip()

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 80:
            raise ValueError("Name must be at most 80 characters")
        return v.strip() if v else v


class PasswordChangeForm(BaseModel):
    """Password change form schema."""

    password: str
    confirm: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(v) < 6 or len(v) > 40:
            raise ValueError("Password must be between 6 and 40 characters")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordChangeForm":
        if self.password != self.confirm:
            raise ValueError("Passwords must match")
        return self


class RegisterForm(BaseModel):
    """User registration form schema."""

    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    password: str
    confirm: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or len(v) < 3 or len(v) > 25:
            raise ValueError("Username must be between 3 and 25 characters")
        return v.strip()

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 80:
            raise ValueError("Name must be at most 80 characters")
        return v.strip() if v else v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(v) < 6 or len(v) > 40:
            raise ValueError("Password must be between 6 and 40 characters")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterForm":
        if self.password != self.confirm:
            raise ValueError("Passwords must match")
        return self


class UserResponse(BaseModel):
    """Response model for user data."""

    user_id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    active: bool
    is_admin: bool

    class Config:
        from_attributes = True
