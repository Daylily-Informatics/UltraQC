# -*- coding: utf-8 -*-
"""
User views for FastAPI.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ultraqc.app import get_templates
from ultraqc.auth import get_current_active_user, get_current_admin_user
from ultraqc.database import get_async_session
from ultraqc.user.forms import AdminForm, PasswordChangeForm
from ultraqc.user.models import User

user_router = APIRouter(tags=["users"])


@user_router.get("/", response_class=HTMLResponse)
async def profile(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    Show user profile.
    """
    templates = get_templates()
    return templates.TemplateResponse(
        "users/profile.html",
        {"request": request, "current_user": current_user},
    )


@user_router.get("/multiqc_config", response_class=HTMLResponse)
async def multiqc_config(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    Instructions for MultiQC configuration.
    """
    templates = get_templates()
    return templates.TemplateResponse(
        "users/multiqc_config.html",
        {"request": request, "current_user": current_user},
    )


@user_router.get("/password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    Change user password.
    """
    templates = get_templates()
    return templates.TemplateResponse(
        "users/change_password.html",
        {"request": request, "current_user": current_user, "form": {}},
    )


@user_router.get("/admin/users", response_class=HTMLResponse)
async def manage_users(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Manage users (admin only).
    """
    templates = get_templates()
    result = await session.execute(select(User))
    users_data = result.scalars().all()
    return templates.TemplateResponse(
        "users/manage_users.html",
        {"request": request, "current_user": current_user, "users_data": users_data, "form": {}},
    )
