# -*- coding: utf-8 -*-
"""
Database module for FastAPI with SQLAlchemy 2.0 async support.
"""
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from megaqc.settings import Settings

# Global engine and session factory
_async_engine = None
_sync_engine = None
_async_session_factory: Optional[async_sessionmaker] = None
_sync_session_factory: Optional[sessionmaker] = None


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class CRUDMixin:
    """
    Mixin that adds convenience methods for CRUD (create, read, update, delete)
    operations.
    """

    @classmethod
    def get_or_create(cls, session: Session, **kwargs):
        """Get existing record or create new one."""
        instance = session.query(cls).filter_by(**kwargs).first()
        if instance:
            return instance
        else:
            instance = cls(**kwargs)
            return instance

    @classmethod
    def create(cls, session: Session, **kwargs):
        """
        Create a new record and save it to the database.
        """
        instance = cls(**kwargs)
        session.add(instance)
        session.commit()
        return instance

    def update(self, session: Session, commit: bool = True, **kwargs):
        """
        Update specific fields of a record.
        """
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        if commit:
            session.add(self)
            session.commit()
        return self

    def save(self, session: Session, commit: bool = True):
        """
        Save the record.
        """
        session.add(self)
        if commit:
            session.commit()
        return self

    def delete(self, session: Session, commit: bool = True):
        """
        Remove the record from the database.
        """
        session.delete(self)
        if commit:
            session.commit()

    @property
    def primary_key(self):
        return getattr(self, self.__class__.primary_key_name())

    @classmethod
    def primary_key_columns(cls):
        return inspect(cls).primary_key

    @classmethod
    def primary_key_name(cls):
        return cls.primary_key_columns()[0].name


class SurrogatePK:
    """
    A mixin that adds a surrogate integer 'primary key' column named ``id`` to
    any declarative-mapped class.
    """

    __table_args__ = {"extend_existing": True}

    @classmethod
    def get_by_id(cls, session: Session, record_id):
        """
        Get record by ID.
        """
        if isinstance(record_id, str) and record_id.isdigit():
            record_id = int(record_id)
        if isinstance(record_id, (int, float)):
            return session.get(cls, int(record_id))
        return None


async def init_db_engine(settings: Settings):
    """
    Initialize the database engine.
    """
    global _async_engine, _sync_engine, _async_session_factory, _sync_session_factory

    # Create async engine
    _async_engine = create_async_engine(
        settings.DATABASE_URL_ASYNC,
        echo=settings.DEBUG,
    )

    # Create sync engine for migrations and some operations
    _sync_engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
    )

    # Create session factories
    _async_session_factory = async_sessionmaker(
        _async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    _sync_session_factory = sessionmaker(
        _sync_engine,
        expire_on_commit=False,
    )


async def close_db_engine():
    """
    Close the database engine.
    """
    global _async_engine, _sync_engine
    if _async_engine:
        await _async_engine.dispose()
    if _sync_engine:
        _sync_engine.dispose()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async database session.
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db_engine first.")

    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_session() -> Session:
    """
    Get a synchronous database session.
    """
    if _sync_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db_engine first.")

    return _sync_session_factory()


def get_sync_engine():
    """Get the synchronous engine."""
    return _sync_engine


def postgres_create_user(username, conn, cur, password=None):
    """
    Create a postgres user, including a password if provided.
    """
    from psycopg2.errors import DuplicateObject
    from psycopg2.sql import SQL, Identifier, Placeholder

    try:
        if password:
            cur.execute(
                SQL("CREATE USER {} WITH ENCRYPTED PASSWORD {}").format(
                    Identifier(username), Placeholder()
                ),
                [password],
            )
        else:
            cur.execute(SQL("CREATE USER {}").format(Identifier(username)))

        print(f"User {username} created successfully")
    except DuplicateObject:
        print(f"User {username} already exists")


def postgres_create_database(conn, cur, database, user):
    """
    Create a Postgres database, with the given owner.
    """
    from psycopg2.sql import SQL, Identifier

    cur.execute(
        SQL("CREATE DATABASE {} OWNER {}").format(
            Identifier(database), Identifier(user)
        )
    )
    print("Database created successfully")


def init_db(url: str):
    """
    Initialize a new database (synchronous version for CLI).
    """
    if "postgresql" in url:
        import psycopg2

        try:
            engine = create_engine(url, echo=True)
            engine.connect().close()

        except (OperationalError, psycopg2.OperationalError):
            config_url = make_url(url)
            postgres_url = URL.create(
                database="postgres",
                username="postgres",
                password=None,
                drivername=config_url.drivername,
                host=config_url.host,
                port=config_url.port,
                query=config_url.query,
            )

            default_engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
            conn = default_engine.raw_connection()

            with conn.cursor() as cur:
                print("Initializing the postgres user")
                postgres_create_user(
                    config_url.username,
                    conn=conn,
                    cur=cur,
                    password=config_url.password,
                )
            with conn.cursor() as cur:
                print("Initializing the postgres database")
                postgres_create_database(
                    conn=conn,
                    cur=cur,
                    database=config_url.database,
                    user=config_url.username,
                )

            engine = create_engine(url, echo=True)
            engine.connect().close()
    else:
        engine = create_engine(url, echo=True)

    # Import models to ensure they're registered
    from megaqc.model import models  # noqa
    from megaqc.user import models as user_models  # noqa

    # Create all tables
    Base.metadata.create_all(engine)

    print("Initialized the database.")
