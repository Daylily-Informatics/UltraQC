#!/usr/bin/env python

"""
UltraQC: a web application that collects results from multiple runs of MultiQC and allows
bulk visualisation.
"""

import asyncio
import os
import sys
from typing import Optional

import click
import sqlalchemy
import uvicorn
from environs import Env

from ultraqc import settings
from ultraqc.version import get_version, get_version_info

env = Env()


def get_config():
    """Get the appropriate configuration based on environment."""
    from ultraqc.settings import DevConfig, ProdConfig, TestConfig

    if env.bool("ULTRAQC_PRODUCTION", False):
        return ProdConfig()
    elif env.bool("ULTRAQC_TEST", False):
        return TestConfig()
    else:
        # Default to dev config for local development
        return DevConfig()


def check_database(config):
    """Check if the database is initialized."""
    try:
        dbengine = sqlalchemy.create_engine(config.DATABASE_URL).connect()
        metadata = sqlalchemy.MetaData()
        metadata.reflect(bind=dbengine)
        if "sample_data" not in metadata.tables:
            print("\n##### ERROR! Could not find table 'sample_data' in database!")
            print(
                "Has the database been initialised? If not, please run 'ultraqc initdb' first"
            )
            print("Exiting...\n")
            sys.exit(1)
        dbengine.close()
    except Exception as e:
        print(f"\n##### ERROR! Could not connect to database: {e}")
        print("Exiting...\n")
        sys.exit(1)


def create_ultraqc_app():
    """Create the FastAPI application."""
    from ultraqc.app import create_app

    config = get_config()
    return create_app(config)


@click.group()
@click.pass_context
def cli(ctx):
    """
    Welcome to the UltraQC command line interface.

    \nSee below for the available commands - for example,
    to start the UltraQC server, use the command: ultraqc run
    """
    ctx.ensure_object(dict)


@cli.command()
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--workers", "-w", default=1, help="Number of worker processes")
def run(host: str, port: int, reload: bool, workers: int):
    """Run the UltraQC web server."""
    config = get_config()

    if settings.run_db_check:
        check_database(config)

    print(f" * Starting UltraQC server on http://{host}:{port}")

    uvicorn.run(
        "ultraqc.app:create_app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        factory=True,
    )


@cli.command()
def initdb():
    """Initialize the database."""
    from ultraqc.database import init_db

    config = get_config()
    print("Initializing database...")
    init_db(config.DATABASE_URL)
    print("Database initialized successfully!")


@cli.command()
def shell():
    """Start an interactive Python shell with app context."""
    import code

    app = create_ultraqc_app()
    banner = f"UltraQC Interactive Shell\nApp: {app}"
    ctx = {"app": app}
    code.interact(banner=banner, local=ctx)


def main():
    # Get version from GitHub releases or fallback to local
    version = get_version(include_git_hash=True)
    version_info = get_version_info()

    print(f"This is UltraQC v{version}")
    print(f" * Version source: {version_info['source']}")

    if version_info['git_hash_short']:
        print(f" * Git commit: {version_info['git_hash_short']}")
    print()

    if env.bool("ULTRAQC_DEBUG", False):
        print(" * Environment variable ULTRAQC_DEBUG is true - running in dev mode")
    elif not env.bool("ULTRAQC_PRODUCTION", False):
        print(" * Running in test mode")

    # Set run_db_check for commands that need it
    settings.run_db_check = True
    cli()


if __name__ == "__main__":
    main()
