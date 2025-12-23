"""
Tests for current user API endpoint.

NOTE: These tests are being migrated from Flask to FastAPI.
"""
import pytest

from megaqc.model import models
from tests import factories


@pytest.mark.asyncio
async def test_current_user_session_working(db_session, client, token):
    """
    Test the current_user endpoint, using a valid token.

    This should work.
    """
    # Create a user
    user = factories.UserFactory.build()
    user.set_password("password")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Make request with the user's token
    response = await client.get(
        "/rest_api/v1/users/current",
        headers={"access_token": user.api_token}
    )

    # Check the request was successful
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_current_user_session_invalid(db_session, client):
    """
    Test the current_user endpoint without authentication.

    This should fail with 401.
    """
    # Create a user but don't authenticate
    user = factories.UserFactory.build()
    user.set_password("password")
    db_session.add(user)
    await db_session.commit()

    response = await client.get("/rest_api/v1/users/current")

    # Check the request was unauthorized
    assert response.status_code == 401
