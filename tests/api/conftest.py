import pytest
import pytest_asyncio

from tests import factories


@pytest_asyncio.fixture(scope="function")
async def token(db_session) -> str:
    """Create a regular user and return their API token."""
    user = factories.UserFactory.build(is_admin=False)
    user.set_password("password")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.api_token


@pytest_asyncio.fixture(scope="function")
async def admin_token(db_session) -> str:
    """Create an admin user and return their API token."""
    user = factories.UserFactory.build(is_admin=True)
    user.set_password("password")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.api_token
