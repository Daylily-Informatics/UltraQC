"""
REST API for FastAPI.

RESTful API following JSON API patterns where relevant.
"""
from hashlib import sha1
from http import HTTPStatus
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

import ultraqc.user.models as user_models
from ultraqc.auth import get_current_active_user, get_current_admin_user, get_current_user
from ultraqc.database import get_async_session
from ultraqc.model import models
from ultraqc.rest_api import plot, schemas, utils

rest_api_router = APIRouter(tags=["rest_api"])


# Pydantic response models
class UploadResponse(BaseModel):
    id: int
    status: str
    path: Optional[str] = None
    message: Optional[str] = None
    user_id: int

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    report_id: int
    title: str
    created_at: Optional[str] = None
    user_id: Optional[int] = None

    class Config:
        from_attributes = True


class SampleResponse(BaseModel):
    sample_id: int
    sample_name: str
    report_id: int

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    active: bool
    is_admin: bool

    class Config:
        from_attributes = True


# Upload endpoints
@rest_api_router.get("/uploads")
async def list_uploads(
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """List all uploads."""
    result = await session.execute(select(models.Upload))
    uploads = result.scalars().all()
    return [{"id": u.upload_id, "status": u.status, "message": u.message, "user_id": u.user_id} for u in uploads]


@rest_api_router.get("/uploads/{upload_id}")
async def get_upload(
    upload_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get a specific upload."""
    result = await session.execute(select(models.Upload).where(models.Upload.upload_id == upload_id))
    upload = result.scalar_one_or_none()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return {"id": upload.upload_id, "status": upload.status, "message": upload.message, "user_id": upload.user_id}


@rest_api_router.post("/uploads", status_code=status.HTTP_201_CREATED)
async def create_upload(
    report: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Upload a new report."""
    file_name = utils.get_unique_filename()
    content = await report.read()
    with open(file_name, "wb") as f:
        f.write(content)

    upload_row = models.Upload(
        status="NOT TREATED",
        path=file_name,
        message="File has been created, loading in UltraQC is queued.",
        user_id=user.user_id,
    )
    session.add(upload_row)
    await session.commit()
    await session.refresh(upload_row)

    return {"id": upload_row.upload_id, "status": upload_row.status, "message": upload_row.message}


# Report endpoints
@rest_api_router.get("/reports")
async def list_reports(
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """List all reports."""
    result = await session.execute(select(models.Report))
    reports = result.scalars().all()
    return [{"report_id": r.report_id, "title": r.title, "user_id": r.user_id} for r in reports]


@rest_api_router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get a specific report."""
    result = await session.execute(select(models.Report).where(models.Report.report_id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report_id": report.report_id, "title": report.title, "user_id": report.user_id}


# Sample endpoints
@rest_api_router.get("/samples")
async def list_samples(
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """List all samples."""
    result = await session.execute(select(models.Sample))
    samples = result.scalars().all()
    return [{"sample_id": s.sample_id, "sample_name": s.sample_name, "report_id": s.report_id} for s in samples]


@rest_api_router.get("/samples/{sample_id}")
async def get_sample(
    sample_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get a specific sample."""
    result = await session.execute(select(models.Sample).where(models.Sample.sample_id == sample_id))
    sample = result.scalar_one_or_none()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    return {"sample_id": sample.sample_id, "sample_name": sample.sample_name, "report_id": sample.report_id}


# Report Meta endpoints
@rest_api_router.get("/report_meta")
async def list_report_meta(
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """List all report metadata."""
    result = await session.execute(select(models.ReportMeta))
    metas = result.scalars().all()
    return [{"id": m.report_meta_id, "key": m.report_meta_key, "value": m.report_meta_value} for m in metas]


@rest_api_router.get("/meta_types")
async def list_meta_types(
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[str]:
    """List distinct report meta types."""
    result = await session.execute(
        select(distinct(models.ReportMeta.report_meta_key))
    )
    return [row[0] for row in result.all()]


# Sample Data endpoints
@rest_api_router.get("/sample_data")
async def list_sample_data(
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """List all sample data."""
    result = await session.execute(select(models.SampleData))
    data = result.scalars().all()
    return [{"id": d.sample_data_id, "value": d.value, "sample_id": d.sample_id} for d in data]


# Data Type endpoints
@rest_api_router.get("/data_types")
async def list_data_types(
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """List all data types."""
    result = await session.execute(select(models.SampleDataType))
    types = result.scalars().all()
    return [{"id": t.sample_data_type_id, "key": t.data_key, "section": t.data_section} for t in types]


# User endpoints
@rest_api_router.get("/users")
async def list_users(
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """List all users."""
    result = await session.execute(select(user_models.User))
    users = result.scalars().all()
    return [
        {"user_id": u.user_id, "username": u.username, "email": u.email, "active": u.active, "is_admin": u.is_admin}
        for u in users
    ]


@rest_api_router.get("/users/current")
async def get_current_user_info(
    user: user_models.User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get current user info."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "active": user.active,
        "is_admin": user.is_admin,
        "api_token": user.api_token,
    }


@rest_api_router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get a specific user."""
    result = await session.execute(select(user_models.User).where(user_models.User.user_id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": target_user.user_id,
        "username": target_user.username,
        "email": target_user.email,
        "active": target_user.active,
        "is_admin": target_user.is_admin,
    }


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@rest_api_router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: CreateUserRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[user_models.User] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new user."""
    new_user = user_models.User(
        username=user_data.username,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
    )
    await new_user.enforce_admin_async(session)
    new_user.set_password(user_data.password)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return {"user_id": new_user.user_id, "username": new_user.username, "email": new_user.email}


# Filter endpoints
@rest_api_router.get("/filters")
async def list_filters(
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """List all filters."""
    result = await session.execute(select(models.SampleFilter))
    filters = result.scalars().all()
    return [
        {"id": f.sample_filter_id, "name": f.sample_filter_name, "tag": f.sample_filter_tag, "user_id": f.user_id}
        for f in filters
    ]


@rest_api_router.get("/filter_groups")
async def list_filter_groups(
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[str]:
    """List distinct filter groups."""
    result = await session.execute(
        select(distinct(models.SampleFilter.sample_filter_tag))
    )
    return [row[0] for row in result.all() if row[0]]


# Favourite Plot endpoints
@rest_api_router.get("/favourites")
async def list_favourites(
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """List all favourite plots."""
    result = await session.execute(select(models.PlotFavourite))
    favs = result.scalars().all()
    return [
        {"id": f.plot_favourite_id, "title": f.title, "plot_type": f.plot_type, "user_id": f.user_id}
        for f in favs
    ]


@rest_api_router.get("/favourites/{favourite_id}")
async def get_favourite(
    favourite_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get a specific favourite plot."""
    result = await session.execute(
        select(models.PlotFavourite).where(models.PlotFavourite.plot_favourite_id == favourite_id)
    )
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(status_code=404, detail="Favourite not found")
    return {"id": fav.plot_favourite_id, "title": fav.title, "plot_type": fav.plot_type, "data": fav.data}


# Dashboard endpoints
@rest_api_router.get("/dashboards")
async def list_dashboards(
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """List all dashboards."""
    result = await session.execute(select(models.Dashboard))
    dashboards = result.scalars().all()
    return [
        {"id": d.dashboard_id, "title": d.title, "is_public": d.is_public, "user_id": d.user_id}
        for d in dashboards
    ]


@rest_api_router.get("/dashboards/{dashboard_id}")
async def get_dashboard(
    dashboard_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get a specific dashboard."""
    result = await session.execute(
        select(models.Dashboard).where(models.Dashboard.dashboard_id == dashboard_id)
    )
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return {"id": dashboard.dashboard_id, "title": dashboard.title, "data": dashboard.data, "is_public": dashboard.is_public}


# Trend data endpoint
class TrendQueryParams(BaseModel):
    filter_id: Optional[int] = None
    data_type_id: Optional[int] = None
    center: Optional[str] = "mean"
    spread: Optional[str] = "stddev"


@rest_api_router.get("/plots/trends/series")
async def get_trend_series(
    filter_id: Optional[int] = Query(None),
    data_type_id: Optional[int] = Query(None),
    center: str = Query("mean"),
    spread: str = Query("stddev"),
    request: Request = None,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """Get trend series data for plotting."""
    # Generate unique ID for caching
    query_string = str(request.query_params) if request else ""
    request_hash = sha1(query_string.encode()).hexdigest()

    # Call the plot function
    plots = await plot.trend_data_async(
        session,
        plot_prefix=request_hash,
        filter_id=filter_id,
        data_type_id=data_type_id,
        center=center,
        spread=spread,
    )

    return plots


# User-specific resource endpoints
@rest_api_router.get("/users/{user_id}/uploads")
async def get_user_uploads(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """Get uploads for a specific user."""
    result = await session.execute(select(models.Upload).where(models.Upload.user_id == user_id))
    uploads = result.scalars().all()
    return [{"id": u.upload_id, "status": u.status, "message": u.message} for u in uploads]


@rest_api_router.get("/users/{user_id}/reports")
async def get_user_reports(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """Get reports for a specific user."""
    result = await session.execute(select(models.Report).where(models.Report.user_id == user_id))
    reports = result.scalars().all()
    return [{"report_id": r.report_id, "title": r.title} for r in reports]


@rest_api_router.get("/users/{user_id}/filters")
async def get_user_filters(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """Get filters for a specific user."""
    result = await session.execute(select(models.SampleFilter).where(models.SampleFilter.user_id == user_id))
    filters = result.scalars().all()
    return [{"id": f.sample_filter_id, "name": f.sample_filter_name, "tag": f.sample_filter_tag} for f in filters]


@rest_api_router.get("/users/{user_id}/favourites")
async def get_user_favourites(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """Get favourite plots for a specific user."""
    result = await session.execute(select(models.PlotFavourite).where(models.PlotFavourite.user_id == user_id))
    favs = result.scalars().all()
    return [{"id": f.plot_favourite_id, "title": f.title, "plot_type": f.plot_type} for f in favs]


@rest_api_router.get("/users/{user_id}/dashboards")
async def get_user_dashboards(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """Get dashboards for a specific user."""
    result = await session.execute(select(models.Dashboard).where(models.Dashboard.user_id == user_id))
    dashboards = result.scalars().all()
    return [{"id": d.dashboard_id, "title": d.title, "is_public": d.is_public} for d in dashboards]


@rest_api_router.get("/reports/{report_id}/samples")
async def get_report_samples(
    report_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """Get samples for a specific report."""
    result = await session.execute(select(models.Sample).where(models.Sample.report_id == report_id))
    samples = result.scalars().all()
    return [{"sample_id": s.sample_id, "sample_name": s.sample_name} for s in samples]


@rest_api_router.get("/reports/{report_id}/report_meta")
async def get_report_meta(
    report_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """Get metadata for a specific report."""
    result = await session.execute(select(models.ReportMeta).where(models.ReportMeta.report_id == report_id))
    metas = result.scalars().all()
    return [{"id": m.report_meta_id, "key": m.report_meta_key, "value": m.report_meta_value} for m in metas]


@rest_api_router.get("/samples/{sample_id}/sample_data")
async def get_sample_data(
    sample_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: user_models.User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """Get data for a specific sample."""
    result = await session.execute(select(models.SampleData).where(models.SampleData.sample_id == sample_id))
    data = result.scalars().all()
    return [{"id": d.sample_data_id, "value": d.value} for d in data]
