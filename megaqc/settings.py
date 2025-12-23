# -*- coding: utf-8 -*-
"""
Application configuration using Pydantic Settings for FastAPI.
"""
from __future__ import print_function

import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

import yaml
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Flag for database check on startup
run_db_check = False


class Settings(BaseSettings):
    """
    Base configuration using Pydantic Settings.
    """

    model_config = SettingsConfigDict(
        env_prefix="MEGAQC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core settings
    SECRET_KEY: str = "secret-key"  # TODO: Change me in production
    DEBUG: bool = False
    TESTING: bool = False
    ENV: str = "dev"

    # Paths
    APP_DIR: Path = Path(__file__).parent.absolute()
    PROJECT_ROOT: Path = Path(__file__).parent.parent.absolute()

    @computed_field
    @property
    def UPLOAD_FOLDER(self) -> str:
        return str(self.PROJECT_ROOT / "uploads")

    # Logging
    LOG_LEVEL: int = logging.INFO

    # Database settings
    DB_DBMS: str = "sqlite"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "megaqc_user"
    DB_PASS: str = ""
    DB_NAME: str = "megaqc"
    DB_PATH: Optional[str] = None

    # Server settings
    SERVER_NAME: Optional[str] = None

    # Scheduler settings
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_INTERVAL_SECONDS: int = 30

    # User registration
    USER_REGISTRATION_APPROVAL: bool = True

    # Extra config file
    EXTRA_CONFIG: Optional[str] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load extra config from YAML if provided
        if self.EXTRA_CONFIG:
            self._load_extra_config()

    def _load_extra_config(self):
        """Load additional configuration from YAML file."""
        if self.EXTRA_CONFIG and os.path.exists(self.EXTRA_CONFIG):
            with open(self.EXTRA_CONFIG) as f:
                extra_conf = yaml.load(f, Loader=yaml.FullLoader)
                for key, value in extra_conf.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                        if key != "DB_PASS":
                            print(f"Setting {key} to {value}")
                        else:
                            print(f"Setting {key} to ********")
                    else:
                        print(f"Key '{key}' not a valid setting")

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """Build database URL based on settings."""
        if self.DB_DBMS == "sqlite":
            db_path = self.DB_PATH or str(self.PROJECT_ROOT / "megaqc.db")
            return f"sqlite:///{db_path}"
        elif self.DB_HOST.startswith("/"):
            # Unix socket
            return f"{self.DB_DBMS}://{self.DB_USER}:{self.DB_PASS}@/{self.DB_NAME}?host={self.DB_HOST}"
        else:
            return f"{self.DB_DBMS}://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @computed_field
    @property
    def DATABASE_URL_ASYNC(self) -> str:
        """Build async database URL for async SQLAlchemy."""
        if self.DB_DBMS == "sqlite":
            db_path = self.DB_PATH or str(self.PROJECT_ROOT / "megaqc.db")
            return f"sqlite+aiosqlite:///{db_path}"
        elif self.DB_DBMS == "postgresql":
            if self.DB_HOST.startswith("/"):
                return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@/{self.DB_NAME}?host={self.DB_HOST}"
            else:
                return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return self.DATABASE_URL

    @property
    def DATABASE_URL_SANITIZED(self) -> str:
        """Get database URL with password hidden."""
        url = self.DATABASE_URL
        if self.DB_PASS:
            return url.replace(self.DB_PASS, "***")
        return url


class ProdSettings(Settings):
    """
    Production configuration.
    """

    ENV: str = "prod"
    DEBUG: bool = False
    DB_DBMS: str = "postgresql"
    DB_HOST: str = os.environ.get("DB_UNIX_SOCKET", os.environ.get("DB_HOST", "localhost"))
    DB_PORT: int = int(os.environ.get("DB_PORT", "5432"))
    DB_USER: str = os.environ.get("DB_USER", "megaqc")
    DB_PASS: str = os.environ.get("DB_PASS", "megaqcpswd")
    DB_NAME: str = os.environ.get("DB_NAME", "megaqc")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Log to the terminal
        print(" * Environment: Prod", file=sys.stderr)
        print(f" * Database type: {self.DB_DBMS}", file=sys.stderr)
        print(f" * Database path: {self.DATABASE_URL_SANITIZED}", file=sys.stderr)


class DevSettings(Settings):
    """
    Development configuration.
    """

    ENV: str = "dev"
    DEBUG: bool = True
    DB_DBMS: str = "sqlite"
    LOG_LEVEL: int = logging.DEBUG

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Log to the terminal
        print(" * Environment: dev", file=sys.stderr)
        print(f" * Database type: {self.DB_DBMS}", file=sys.stderr)
        print(f" * Database path: {self.DATABASE_URL_SANITIZED}", file=sys.stderr)


class TestSettings(Settings):
    """
    Test configuration.
    """

    DEBUG: bool = True
    TESTING: bool = True
    ENV: str = "test"
    DB_DBMS: str = "sqlite"
    DB_PATH: str = os.path.join(tempfile.mkdtemp(), "megaqc_test.db")
    LOG_LEVEL: int = logging.DEBUG

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Log to the terminal
        print(" * Environment: test", file=sys.stderr)
        print(f" * Database type: {self.DB_DBMS}", file=sys.stderr)
        print(f" * Database path: {self.DATABASE_URL_SANITIZED}", file=sys.stderr)


def get_settings() -> Settings:
    """
    Get settings based on environment variables.
    """
    env = os.environ.get("MEGAQC_ENV", "dev").lower()
    if env == "prod" or os.environ.get("MEGAQC_PRODUCTION", "").lower() in ("true", "1"):
        return ProdSettings()
    elif env == "test" or os.environ.get("MEGAQC_TESTING", "").lower() in ("true", "1"):
        return TestSettings()
    else:
        return DevSettings()


# Backwards compatibility aliases
Config = Settings
ProdConfig = ProdSettings
DevConfig = DevSettings
TestConfig = TestSettings
