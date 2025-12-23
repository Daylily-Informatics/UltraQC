#!/usr/bin/env python

"""
MegaQC: a web application that collects results from multiple runs of MultiQC and allows
bulk visualisation.
"""

import asyncio
import os
import sys
from typing import Optional

import click
import pkg_resources
import sqlalchemy
import uvicorn
from environs import Env

from megaqc import settings

env = Env()


def get_config():
    """Get the appropriate configuration based on environment."""
    from megaqc.settings import DevConfig, ProdConfig, TestConfig

    if env.bool("MEGAQC_DEBUG", False):
        return DevConfig()
    elif env.bool("MEGAQC_PRODUCTION", False):
        return ProdConfig()
    else:
        return TestConfig()


def check_database(config):
    """Check if the database is initialized."""
    try:
        dbengine = sqlalchemy.create_engine(config.SQLALCHEMY_DATABASE_URI).connect()
        metadata = sqlalchemy.MetaData()
        metadata.reflect(bind=dbengine)
        if "sample_data" not in metadata.tables:
            print("\n##### ERROR! Could not find table 'sample_data' in database!")
            print(
                "Has the database been initialised? If not, please run 'megaqc initdb' first"
            )
            print("Exiting...\n")
            sys.exit(1)
        dbengine.close()
    except Exception as e:
        print(f"\n##### ERROR! Could not connect to database: {e}")
        print("Exiting...\n")
        sys.exit(1)


def create_megaqc_app():
    """Create the FastAPI application."""
    from megaqc.app import create_app

    config = get_config()
    return create_app(config)


@click.group()
@click.pass_context
def cli(ctx):
    """
    Welcome to the MegaQC command line interface.

    \nSee below for the available commands - for example,
    to start the MegaQC server, use the command: megaqc run
    """
    ctx.ensure_object(dict)


@cli.command()
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--workers", "-w", default=1, help="Number of worker processes")
def run(host: str, port: int, reload: bool, workers: int):
    """Run the MegaQC web server."""
    config = get_config()

    if settings.run_db_check:
        check_database(config)

    print(f" * Starting MegaQC server on http://{host}:{port}")

    uvicorn.run(
        "megaqc.app:create_app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        factory=True,
    )


@cli.command()
def initdb():
    """Initialize the database."""
    from megaqc.database import init_db

    config = get_config()
    print("Initializing database...")
    asyncio.run(init_db(config.SQLALCHEMY_DATABASE_URI))
    print("Database initialized successfully!")


@cli.command()
def shell():
    """Start an interactive Python shell with app context."""
    import code

    app = create_megaqc_app()
    banner = f"MegaQC Interactive Shell\nApp: {app}"
    ctx = {"app": app}
    code.interact(banner=banner, local=ctx)


def main():
    version = pkg_resources.get_distribution("megaqc").version
    print("This is MegaQC v{}\n".format(version))

    if env.bool("MEGAQC_DEBUG", False):
        print(" * Environment variable MEGAQC_DEBUG is true - running in dev mode")
    elif not env.bool("MEGAQC_PRODUCTION", False):
        print(" * Running in test mode")

    # Set run_db_check for commands that need it
    settings.run_db_check = True
    cli()


if __name__ == "__main__":
    main()
