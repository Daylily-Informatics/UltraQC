# -*- coding: utf-8 -*-
"""
Defines fixtures available to all tests.
"""

import asyncio
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ultraqc.app import create_app
from ultraqc.database import Base, get_async_session
from ultraqc.settings import TestConfig

from .factories import UserFactory


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def multiqc_data():
    here = Path(__file__).parent
    with (here / "multiqc_data.json").open() as fp:
        return fp.read()


@pytest.fixture(scope="function")
def app():
    """
    A FastAPI application for the tests.
    """
    config = TestConfig()
    _app = create_app(config)
    return _app


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create an async engine for tests."""
    config = TestConfig()
    # Use async URL directly
    db_url = config.DATABASE_URL_ASYNC

    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    An async database session for the tests.
    """
    async_session_factory = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(app, db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    An async HTTP client for testing FastAPI.
    """
    # Override the get_async_session dependency
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user(db_session):
    """
    A user for the tests.
    """
    user = UserFactory(password="myprecious")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def session(db_session) -> AsyncSession:
    """Alias for db_session."""
    return db_session


@pytest_asyncio.fixture
async def token(user):
    """
    An API token for the test user.
    """
    return user.api_token


@pytest_asyncio.fixture
async def admin_token(db_session):
    """
    An API token for an admin user.
    """
    admin = UserFactory(password="adminpass", is_admin=True, active=True)
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin.api_token
