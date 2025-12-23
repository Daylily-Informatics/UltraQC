"""
WSGI/ASGI entry point for MegaQC.

This module provides the application instance for ASGI servers like Uvicorn or Gunicorn with uvicorn workers.

Usage with Uvicorn:
    uvicorn megaqc.wsgi:app --host 0.0.0.0 --port 8000

Usage with Gunicorn + Uvicorn workers:
    gunicorn megaqc.wsgi:app -w 4 -k uvicorn.workers.UvicornWorker
"""

from environs import Env

from megaqc.app import create_app
from megaqc.settings import DevConfig, ProdConfig, TestConfig

env = Env()


def get_config():
    """Get the appropriate configuration based on environment."""
    if env.bool("MEGAQC_DEBUG", False):
        return DevConfig()
    elif env.bool("MEGAQC_PRODUCTION", False):
        return ProdConfig()
    else:
        return TestConfig()


# Create the FastAPI application instance
app = create_app(get_config())
