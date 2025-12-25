# -*- coding: utf-8 -*-
"""
Public section, including homepage and signup.

Refactored to use FastAPI with Jinja2 templates.
"""
import json
from collections import OrderedDict
from datetime import timedelta
from typing import Optional
from urllib.parse import unquote_plus

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ultraqc.api.utils import (
    aggregate_new_parameters,
    get_dashboard_data,
    get_dashboards,
    get_favourite_plot_data,
    get_plot_favourites,
    get_queued_uploads,
    get_report_metadata_fields,
    get_reports_data,
    get_samples,
    get_user_filters,
)
from ultraqc.app import get_templates
from ultraqc.auth import (
    ALGORITHM,
    create_access_token,
    get_current_active_user,
    get_current_user,
)
from ultraqc.database import get_async_session
from ultraqc.public.forms import LoginForm
from ultraqc.user.forms import RegisterForm
from ultraqc.user.models import User

public_router = APIRouter(tags=["public"])


@public_router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Home page.
    """
    templates = get_templates()
    return templates.TemplateResponse(
        "public/home.html",
        {
            "request": request,
            "current_user": current_user,
            "num_samples": get_samples(count=True),
            "num_reports": get_reports_data(count=True),
            "num_uploads_processing": get_queued_uploads(
                count=True, filter_cats=["NOT TREATED", "IN TREATMENT"]
            ),
        },
    )


@public_router.get("/login/", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next: Optional[str] = Query(None),
    flash_message: Optional[str] = Query(None),
    flash_category: Optional[str] = Query(None),
):
    """
    Login page (GET).
    """
    templates = get_templates()
    return templates.TemplateResponse(
        "public/login.html",
        {
            "request": request,
            "form": {},
            "flash_message": flash_message,
            "flash_category": flash_category,
        },
    )


@public_router.post("/login/")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    next: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Handle login (POST).
    """
    templates = get_templates()

    # Validate form
    try:
        form = LoginForm(username=username, password=password)
    except ValidationError as e:
        return templates.TemplateResponse(
            "public/login.html",
            {"request": request, "form": {"username": username}, "errors": e.errors()},
        )

    # Find user
    result = await session.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()

    if not user:
        return templates.TemplateResponse(
            "public/login.html",
            {"request": request, "form": {"username": username}, "error": "Unknown username"},
        )

    if not user.check_password(form.password):
        return templates.TemplateResponse(
            "public/login.html",
            {"request": request, "form": {"username": username}, "error": "Invalid password"},
        )

    if not user.active:
        return templates.TemplateResponse(
            "public/login.html",
            {"request": request, "form": {"username": username}, "error": "User not activated"},
        )

    # Create session token
    settings = request.state.settings
    access_token = create_access_token(
        data={"sub": user.user_id}, settings=settings, expires_delta=timedelta(days=7)
    )

    # Redirect with session cookie
    redirect_url = next or "/"
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,  # 7 days
        samesite="lax",
    )
    return response


@public_router.get("/logout/")
async def logout(response: Response):
    """
    Logout.
    """
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="session_token")
    return response


@public_router.get("/register/", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Registration page (GET).
    """
    templates = get_templates()
    return templates.TemplateResponse(
        "public/register.html",
        {"request": request, "form": {}},
    )


@public_router.post("/register/")
async def register(
    request: Request,
    response: Response,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm: str = Form(...),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Handle registration (POST).
    """
    templates = get_templates()

    # Validate form
    try:
        form = RegisterForm(
            username=username,
            email=email,
            password=password,
            confirm=confirm,
            first_name=first_name,
            last_name=last_name,
        )
    except ValidationError as e:
        return templates.TemplateResponse(
            "public/register.html",
            {"request": request, "form": {"username": username, "email": email}, "errors": e.errors()},
        )

    # Check for existing user
    result = await session.execute(select(User).where(User.username == form.username))
    if result.scalar_one_or_none():
        return templates.TemplateResponse(
            "public/register.html",
            {"request": request, "form": {"username": username, "email": email}, "error": "Username already registered"},
        )

    result = await session.execute(select(User).where(User.email == form.email))
    if result.scalar_one_or_none():
        return templates.TemplateResponse(
            "public/register.html",
            {"request": request, "form": {"username": username, "email": email}, "error": "Email already registered"},
        )

    # Create user
    settings = request.state.settings
    user = User(
        username=form.username,
        email=form.email,
        password=form.password,
        first_name=form.first_name,
        last_name=form.last_name,
    )
    await user.enforce_admin_async(session)
    session.add(user)
    await session.commit()

    if user.active:
        # Auto-login for first user
        access_token = create_access_token(
            data={"sub": user.user_id}, settings=settings, expires_delta=timedelta(days=7)
        )
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="session_token",
            value=access_token,
            httponly=True,
            max_age=7 * 24 * 60 * 60,
            samesite="lax",
        )
        return response

    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@public_router.get("/about/", response_class=HTMLResponse)
async def about(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    About page.
    """
    templates = get_templates()
    return templates.TemplateResponse(
        "public/about.html",
        {"request": request, "current_user": current_user},
    )


@public_router.get("/plot_type/", response_class=HTMLResponse)
async def choose_plot_type(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Choose plot type.
    """
    templates = get_templates()
    return templates.TemplateResponse(
        "public/plot_type.html",
        {
            "request": request,
            "current_user": current_user,
            "num_samples": get_samples(count=True),
        },
    )


@public_router.get("/report_plot/", response_class=HTMLResponse)
async def report_plot(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """Report plot page."""
    templates = get_templates()
    return_data = aggregate_new_parameters(session, current_user, [], False)
    sample_filters = order_sample_filters(current_user)
    return templates.TemplateResponse(
        "public/report_plot.html",
        {
            "request": request,
            "current_user": current_user,
            "user_token": current_user.api_token,
            "sample_filters": sample_filters,
            "num_samples": return_data[0],
            "report_fields_json": json.dumps(return_data[1]),
            "sample_fields_json": json.dumps(return_data[2]),
            "report_plot_types": return_data[3],
        },
    )


@public_router.get("/queued_uploads/", response_class=HTMLResponse)
async def queued_uploads(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """Queued uploads page."""
    templates = get_templates()
    return templates.TemplateResponse(
        "users/queued_uploads.html",
        {
            "request": request,
            "current_user": current_user,
            "user_token": current_user.api_token,
            "uploads": get_queued_uploads(),
        },
    )


@public_router.get("/dashboards/", response_class=HTMLResponse)
async def list_dashboard(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """List dashboards."""
    templates = get_templates()
    return templates.TemplateResponse(
        "users/dashboards.html",
        {
            "request": request,
            "current_user": current_user,
            "dashboards": get_dashboards(current_user),
            "user_token": current_user.api_token,
        },
    )


@public_router.get("/dashboard/create/", response_class=HTMLResponse)
async def create_dashboard_page(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """Create dashboard page."""
    templates = get_templates()
    return templates.TemplateResponse(
        "users/create_dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "dashboard_id": None,
            "favourite_plots": get_plot_favourites(current_user),
            "user_token": current_user.api_token,
        },
    )


@public_router.get("/dashboard/edit/{dashboard_id}", response_class=HTMLResponse)
async def edit_dashboard_page(
    request: Request,
    dashboard_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """Edit dashboard page."""
    templates = get_templates()
    return templates.TemplateResponse(
        "users/create_dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "dashboard_id": dashboard_id,
            "favourite_plots": get_plot_favourites(current_user),
            "user_token": current_user.api_token,
        },
    )


@public_router.get("/dashboard/view/{dashboard_id}", response_class=HTMLResponse)
@public_router.get("/dashboard/view/{dashboard_id}/raw", response_class=HTMLResponse)
async def view_dashboard(
    request: Request,
    dashboard_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """View dashboard."""
    templates = get_templates()
    dashboard = get_dashboard_data(current_user, dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return templates.TemplateResponse(
        "public/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "dashboard_id": dashboard_id,
            "dashboard": dashboard,
            "raw": str(request.url.path).endswith("/raw"),
            "user_token": current_user.api_token,
        },
    )


@public_router.get("/plot_favourites/", response_class=HTMLResponse)
async def plot_favourites(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """View and edit saved plots."""
    templates = get_templates()
    return templates.TemplateResponse(
        "users/plot_favourites.html",
        {
            "request": request,
            "current_user": current_user,
            "favourite_plots": get_plot_favourites(current_user),
            "user_token": current_user.api_token,
        },
    )


@public_router.get("/plot_favourite/{fav_id}", response_class=HTMLResponse)
@public_router.get("/plot_favourite/{fav_id}/raw", response_class=HTMLResponse)
async def plot_favourite(
    request: Request,
    fav_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """View a saved plot."""
    templates = get_templates()
    return templates.TemplateResponse(
        "users/plot_favourite.html",
        {
            "request": request,
            "current_user": current_user,
            "plot_data": get_favourite_plot_data(current_user, fav_id),
            "raw": str(request.url.path).endswith("/raw"),
            "user_token": current_user.api_token,
        },
    )


@public_router.get("/edit_filters/", response_class=HTMLResponse)
async def edit_filters(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """Edit saved filters."""
    templates = get_templates()
    sample_filters = order_sample_filters(current_user)
    sample_filter_counts = {}
    for sfg in sample_filters:
        sample_filter_counts[sfg] = {}
        for sf in sample_filters[sfg]:
            sample_filter_counts[sf["id"]] = get_samples(
                filters=sf.get("sample_filter_data", []), count=True
            )
    return templates.TemplateResponse(
        "users/organize_filters.html",
        {
            "request": request,
            "current_user": current_user,
            "sample_filters": sample_filters,
            "sample_filter_counts": sample_filter_counts,
            "user_token": current_user.api_token,
            "num_samples": get_samples(count=True),
        },
    )


def order_sample_filters(current_user: User) -> OrderedDict:
    """Order sample filters by set."""
    sample_filters = OrderedDict()
    sample_filters["Global"] = [{"id": -1, "set": "Global", "name": "All Samples"}]
    for sf in get_user_filters(current_user):
        if sf["set"] not in sample_filters:
            sample_filters[sf["set"]] = list()
        sample_filters[sf["set"]].append(sf)
    return sample_filters


@public_router.get("/distributions/", response_class=HTMLResponse)
async def distributions(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """Distributions page."""
    templates = get_templates()
    return_data = aggregate_new_parameters(session, current_user, [], False)
    sample_filters = order_sample_filters(current_user)
    return templates.TemplateResponse(
        "public/distributions.html",
        {
            "request": request,
            "current_user": current_user,
            "user_token": current_user.api_token,
            "sample_filters": sample_filters,
            "num_samples": return_data[0],
            "report_fields": return_data[1],
            "sample_fields": return_data[2],
            "report_fields_json": json.dumps(return_data[1]),
            "sample_fields_json": json.dumps(return_data[2]),
        },
    )


@public_router.get("/trends/", response_class=HTMLResponse)
async def trends(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Trends page (React)."""
    templates = get_templates()
    return templates.TemplateResponse(
        "public/react.html",
        {"request": request, "current_user": current_user, "entrypoint": "trend"},
    )


@public_router.get("/admin/", response_class=HTMLResponse)
async def admin(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Admin page (React)."""
    templates = get_templates()
    return templates.TemplateResponse(
        "public/react.html",
        {"request": request, "current_user": current_user, "entrypoint": "admin"},
    )


@public_router.get("/comparisons/", response_class=HTMLResponse)
async def comparisons(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """Comparisons page."""
    templates = get_templates()
    return_data = aggregate_new_parameters(session, current_user, [], False)
    sample_filters = order_sample_filters(current_user)
    return templates.TemplateResponse(
        "public/comparisons.html",
        {
            "request": request,
            "current_user": current_user,
            "user_token": current_user.api_token,
            "sample_filters": sample_filters,
            "num_samples": return_data[0],
            "report_fields": return_data[1],
            "sample_fields": return_data[2],
            "report_fields_json": json.dumps(return_data[1]),
            "sample_fields_json": json.dumps(return_data[2]),
        },
    )


@public_router.get("/edit_reports/", response_class=HTMLResponse)
async def edit_reports(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """Edit reports page."""
    templates = get_templates()
    user_id = None
    if not current_user.is_admin:
        user_id = current_user.user_id
    return_data = get_reports_data(count=False, user_id=user_id)
    return templates.TemplateResponse(
        "public/reports_management.html",
        {
            "request": request,
            "current_user": current_user,
            "report_data": return_data,
            "report_meta_fields": get_report_metadata_fields(),
            "api_token": current_user.api_token,
        },
    )


@public_router.get("/not_implemented")
async def not_implemented(request: Request):
    """Not implemented placeholder."""
    referer = request.headers.get("referer", "/")
    return RedirectResponse(url=referer, status_code=status.HTTP_302_FOUND)
