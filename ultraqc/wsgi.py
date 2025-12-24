"""
WSGI/ASGI entry point for UltraQC.

This module provides the application instance for ASGI servers like Uvicorn or Gunicorn with uvicorn workers.

Usage with Uvicorn:
    uvicorn ultraqc.wsgi:app --host 0.0.0.0 --port 8000

Usage with Gunicorn + Uvicorn workers:
    gunicorn ultraqc.wsgi:app -w 4 -k uvicorn.workers.UvicornWorker
"""

from environs import Env

from ultraqc.app import create_app
from ultraqc.settings import DevConfig, ProdConfig, TestConfig

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
