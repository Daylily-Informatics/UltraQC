# -*- coding: utf-8 -*-
"""
User models.
"""
import datetime as dt
import string
from builtins import str
from typing import Optional

from passlib.hash import argon2
from passlib.utils import getrandstr, rng
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    UnicodeText,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from ultraqc.database import Base

letters = string.ascii_letters
digits = string.digits


class Role(Base):
    """
    A role for a user.
    """

    __tablename__ = "roles"
    role_id = Column(Integer, primary_key=True)
    name = Column(UnicodeText, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"))

    user = relationship("User", back_populates="roles")

    def __repr__(self):
        """
        Represent instance as a unique string.
        """
        return "<Role({name})>".format(name=self.name)


class User(Base):
    """
    A user of the app.
    """

    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    username = Column(UnicodeText, unique=True, nullable=False)
    email = Column(UnicodeText, unique=True, nullable=False)
    salt = Column(UnicodeText, nullable=True)
    password = Column(UnicodeText, nullable=True)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    first_name = Column(UnicodeText, nullable=True)
    last_name = Column(UnicodeText, nullable=True)
    active = Column(Boolean(), default=False)
    is_admin = Column(Boolean(), default=False)
    api_token = Column(UnicodeText, nullable=True)

    reports = relationship("Report", back_populates="user")
    uploads = relationship("Upload", back_populates="user")
    roles = relationship("Role", back_populates="user")
    filters = relationship("SampleFilter", back_populates="user")
    favourite_plots = relationship("PlotFavourite", back_populates="user")
    dashboards = relationship("Dashboard", back_populates="user")

    def __init__(self, password: Optional[str] = None, active: Optional[bool] = None, **kwargs):
        """
        Create instance.
        """
        super().__init__(**kwargs)

        # Default active status (can be overridden by settings)
        if active is not None:
            self.active = active
        elif "active" not in kwargs:
            self.active = True  # Default to active, settings can override

        self.salt = getrandstr(rng, digits + letters, 80)
        self.api_token = getrandstr(rng, digits + letters, 80)
        if password:
            self.set_password(password)
        else:
            self.password = None

    async def enforce_admin_async(self, session: AsyncSession):
        """
        Enforce that the first user is an active admin (async version).

        This is included as a method that isn't automatically called, because there are
        cases where we don't want this behaviour to happen, such as during testing.
        """
        result = await session.execute(select(func.count(User.user_id)))
        count = result.scalar()
        if count == 0:
            self.is_admin = True
            self.active = True

    @hybrid_property
    def full_name(self):
        first = self.first_name or ""
        last = self.last_name or ""
        return f"{first} {last}".strip()

    def reset_password(self) -> str:
        """Reset password to a random string and return it."""
        password = getrandstr(rng, digits + letters, 10)
        self.set_password(password)
        return password

    def set_password(self, password: str):
        """
        Set password.
        """
        self.password = argon2.using(rounds=4).hash(password + self.salt)

    def check_password(self, value: str) -> bool:
        """
        Check password.
        """
        if not self.password or not self.salt:
            return False
        return argon2.verify(value + self.salt, self.password)

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return True

    @property
    def is_anonymous(self) -> bool:
        """Check if user is anonymous."""
        return False

    def get_id(self) -> str:
        """Get user ID as string."""
        return str(self.user_id)

    def __repr__(self):
        """
        Represent instance as a unique string.
        """
        return "<User({username!r})>".format(username=self.username)
