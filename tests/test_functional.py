# -*- coding: utf-8 -*-
"""
Functional tests using FastAPI TestClient.
"""
import pytest
from sqlalchemy import select

from megaqc.user.models import User

from .factories import UserFactory


@pytest.fixture()
def user_attrs():
    return UserFactory.build()


class TestLoggingIn:
    """
    Login tests.
    """

    @pytest.mark.asyncio
    async def test_can_log_in_returns_200(self, user, client):
        """
        Login successful.
        """
        # Post login form
        response = await client.post(
            "/login",
            data={"username": user.username, "password": "myprecious"},
            follow_redirects=True,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_sees_alert_on_log_out(self, user, client):
        """
        Show alert on logout.
        """
        # Login first
        await client.post(
            "/login",
            data={"username": user.username, "password": "myprecious"},
            follow_redirects=True,
        )
        # Logout
        response = await client.get("/logout", follow_redirects=True)
        assert response.status_code == 200
        assert "logged out" in response.text.lower()

    @pytest.mark.asyncio
    async def test_sees_error_message_if_password_is_incorrect(self, user, client):
        """
        Show error if password is incorrect.
        """
        response = await client.post(
            "/login",
            data={"username": user.username, "password": "wrong"},
        )
        assert "Invalid password" in response.text or response.status_code == 401

    @pytest.mark.asyncio
    async def test_sees_error_message_if_username_doesnt_exist(self, user, client):
        """
        Show error if username doesn't exist.
        """
        response = await client.post(
            "/login",
            data={"username": "unknown", "password": "myprecious"},
        )
        assert "Unknown user" in response.text or response.status_code == 401


class TestRegistering:
    """
    Register a user.
    """

    @pytest.mark.asyncio
    async def test_can_register(self, user, client, db_session, user_attrs):
        """
        Register a new user.
        """
        result = await db_session.execute(select(User))
        old_count = len(result.scalars().all())

        # Submit registration form
        response = await client.post(
            "/register",
            data={
                "username": user_attrs.username,
                "email": user_attrs.email,
                "first_name": user_attrs.first_name,
                "last_name": user_attrs.last_name,
                "password": "secret",
                "confirm": "secret",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        # Check that a new user was created
        result = await db_session.execute(select(User))
        assert len(result.scalars().all()) == old_count + 1

    @pytest.mark.asyncio
    async def test_sees_error_message_if_passwords_dont_match(
        self, user, client, user_attrs
    ):
        """
        Show error if passwords don't match.
        """
        response = await client.post(
            "/register",
            data={
                "username": user_attrs.username,
                "email": user_attrs.email,
                "first_name": user_attrs.first_name,
                "last_name": user_attrs.last_name,
                "password": "secret",
                "confirm": "secrets",
            },
        )
        assert "Passwords must match" in response.text or response.status_code == 422

    @pytest.mark.asyncio
    async def test_sees_error_message_if_user_already_registered(
        self, user, client, db_session, user_attrs
    ):
        """
        Show error if user already registered.
        """
        # Create a registered user
        existing_user = UserFactory.build(active=True)
        existing_user.set_password("password")
        db_session.add(existing_user)
        await db_session.commit()

        # Try to register with same username
        response = await client.post(
            "/register",
            data={
                "username": existing_user.username,
                "email": user_attrs.email,
                "first_name": user_attrs.first_name,
                "last_name": user_attrs.last_name,
                "password": "secret",
                "confirm": "secret",
            },
        )
        assert "already registered" in response.text.lower() or response.status_code == 400
