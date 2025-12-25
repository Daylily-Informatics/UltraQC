# -*- coding: utf-8 -*-
"""
UltraQC: A web-based tool to collect and visualise data from multiple MultiQC reports.

This file contains the FastAPI app module, with the app factory function.
"""

from __future__ import print_function

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import markdown
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from ultraqc import version
from ultraqc.settings import Settings, get_settings


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_hex(32)

# Templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

# Jinja2 templates - will be configured in create_app
templates: Optional[Jinja2Templates] = None


def safe_markdown(text: str) -> Markup:
    """Convert markdown to HTML safely."""
    return Markup(markdown.markdown(text))


# Route name to URL path mapping for url_for compatibility
ROUTE_MAP = {
    # Public routes
    "public.home": "/",
    "public.about": "/about",
    "public.login": "/login",
    "public.logout": "/logout",
    "public.register": "/register",
    "public.choose_plot_type": "/new_plot",
    "public.report_plot": "/report_plot",
    "public.distributions": "/distributions",
    "public.trends": "/trends",
    "public.comparisons": "/comparisons",
    "public.list_dashboard": "/dashboards",
    "public.create_dashboard": "/dashboards/new",
    "public.plot_favourites": "/favourites",
    "public.queued_uploads": "/uploads",
    "public.edit_filters": "/filters",
    "public.edit_reports": "/reports",
    "public.admin": "/admin",
    # User routes
    "user.profile": "/users/profile",
    "user.multiqc_config": "/users/multiqc_config",
    "user.manage_users": "/users/manage",
    "user.change_password": "/users/change_password",
    # Static files
    "static": "/static",
}


def url_for(endpoint: str, **kwargs) -> str:
    """
    Generate URL for an endpoint.

    This provides Flask-like url_for functionality for templates.
    """
    if endpoint == "static":
        filename = kwargs.get("filename", "")
        return f"/static/{filename}"

    base_url = ROUTE_MAP.get(endpoint, f"/{endpoint}")

    # Handle path parameters
    for key, value in kwargs.items():
        if f"{{{key}}}" in base_url:
            base_url = base_url.replace(f"{{{key}}}", str(value))
        elif f"<{key}>" in base_url:
            base_url = base_url.replace(f"<{key}>", str(value))

    return base_url


def get_flashed_messages_func(request: Request):
    """
    Get flashed messages from session.

    Returns a function that can be called in templates.
    """
    def get_flashed_messages(with_categories: bool = False):
        """Get and clear flash messages from session."""
        messages = getattr(request.state, "flash_messages", [])
        # Clear messages after reading
        request.state.flash_messages = []
        if with_categories:
            return messages
        return [msg for _, msg in messages]
    return get_flashed_messages


def get_templates() -> Jinja2Templates:
    """Get or create templates instance."""
    global templates
    if templates is None:
        templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
        templates.env.filters["safe_markdown"] = safe_markdown
        # Add url_for to globals
        templates.env.globals["url_for"] = url_for
        # Add csrf_token function to globals
        templates.env.globals["csrf_token"] = generate_csrf_token
    return templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    from ultraqc.database import close_db_engine, init_db_engine
    from ultraqc.scheduler import init_scheduler, shutdown_scheduler

    settings = app.state.settings

    # Initialize database engine
    await init_db_engine(settings)

    # Initialize scheduler if enabled
    if settings.SCHEDULER_ENABLED:
        init_scheduler(app, settings.DATABASE_URL)

    yield

    # Shutdown
    await close_db_engine()
    shutdown_scheduler()


def create_app(config: Optional[Settings] = None) -> FastAPI:
    """
    An application factory for FastAPI.

    :param config: The configuration object to use. If None, uses get_settings().
    """
    if config is None:
        config = get_settings()
    elif isinstance(config, type):
        # If a class was passed, instantiate it
        config = config()

    app = FastAPI(
        title="UltraQC",
        description="Collect and visualise data from multiple MultiQC reports",
        version=version,
        lifespan=lifespan,
        debug=config.DEBUG,
    )

    # Store settings in app state
    app.state.settings = config

    # Configure logging
    logging.basicConfig(level=config.LOG_LEVEL)
    logger = logging.getLogger("ultraqc")
    logger.setLevel(config.LOG_LEVEL)

    if config.SERVER_NAME is not None:
        print(f" * Server name: {config.SERVER_NAME}")

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Initialize templates
    get_templates()

    # Register routers
    register_routers(app)

    # Register error handlers
    register_error_handlers(app)

    # Add template context processor middleware
    @app.middleware("http")
    async def add_template_globals(request: Request, call_next):
        """Add global variables to request state for templates."""
        request.state.debug = config.DEBUG
        request.state.version = version
        request.state.settings = config
        response = await call_next(request)
        return response

    return app


def register_routers(app: FastAPI):
    """
    Register FastAPI routers.
    """
    from ultraqc.api.views import api_router
    from ultraqc.public.views import public_router
    from ultraqc.rest_api.views import rest_api_router
    from ultraqc.user.views import user_router

    app.include_router(public_router)
    app.include_router(user_router, prefix="/users")
    app.include_router(api_router, prefix="/api")
    app.include_router(rest_api_router, prefix="/rest_api/v1")


def register_error_handlers(app: FastAPI):
    """
    Register error handlers.
    """
    from fastapi.exceptions import HTTPException, RequestValidationError

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        error_code = exc.status_code
        err_msg = str(exc.detail)

        logger = logging.getLogger("ultraqc")
        logger.error(f"HTTP {error_code}: {err_msg}")

        # Return JSON if an API call
        if request.url.path.startswith("/api/") or request.url.path.startswith("/rest_api/"):
            return JSONResponse(
                status_code=error_code,
                content={
                    "success": False,
                    "message": err_msg,
                    "error": {"code": error_code, "message": err_msg},
                },
            )

        # Return HTML error if not an API call
        tmpl = get_templates()
        if error_code in [401, 404, 500]:
            return HTMLResponse(
                content=tmpl.get_template(f"{error_code}.html").render(
                    request=request, error=exc
                ),
                status_code=error_code,
            )
        else:
            return HTMLResponse(
                content=tmpl.get_template("error.html").render(
                    request=request, error=exc
                ),
                status_code=error_code,
            )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Validation error",
                "error": {"code": 422, "details": exc.errors()},
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger = logging.getLogger("ultraqc")
        logger.exception(f"Unhandled exception: {exc}")

        # Return JSON if an API call
        if request.url.path.startswith("/api/") or request.url.path.startswith("/rest_api/"):
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Internal server error",
                    "error": {"code": 500, "message": str(exc)},
                },
            )

        # Return HTML error
        tmpl = get_templates()
        return HTMLResponse(
            content=tmpl.get_template("500.html").render(request=request, error=exc),
            status_code=500,
        )
