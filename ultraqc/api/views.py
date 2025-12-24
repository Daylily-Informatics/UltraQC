# -*- coding: utf-8 -*-
"""
API views for FastAPI.
"""
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from ultraqc.api.utils import (
    aggregate_new_parameters,
    delete_report_data,
    generate_comparison_plot,
    generate_distribution_plot,
    generate_report_plot,
    generate_trend_plot,
    get_dashboard_data,
    get_favourite_plot_data,
    get_filter_from_data,
    get_queued_uploads,
    get_report_metadata_fields,
    get_reports_data,
    get_sample_fields_values,
    get_sample_metadata_fields,
    get_samples,
    get_timeline_sample_data,
    get_user_filters,
    handle_report_data,
    save_dashboard_data,
    save_plot_favourite_data,
    store_report_data,
    update_fav_report_plot_type,
    update_user_filter,
)
from ultraqc.auth import get_current_active_user, get_current_admin_user
from ultraqc.database import get_async_session
from ultraqc.model.models import Dashboard, PlotData, PlotFavourite, Report, SampleFilter
from ultraqc.user.forms import AdminForm
from ultraqc.user.models import User

api_router = APIRouter(tags=["api"])


# Pydantic models for request/response
class SuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None


class TestResponse(BaseModel):
    success: bool
    name: str
    message: str


@api_router.get("/test")
async def test(
    user: User = Depends(get_current_active_user),
) -> TestResponse:
    """Test API endpoint."""
    return TestResponse(
        success=True, name=user.username, message="Test API call successful"
    )


@api_router.post("/test_post")
async def test_post(
    request: Request,
    user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Test POST endpoint."""
    data = await request.json()
    data["name"] = user.username
    return data


@api_router.post("/upload_data")
async def queue_multiqc_data(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
    file: Optional[UploadFile] = File(None),
) -> JSONResponse:
    """Upload MultiQC data."""
    data = await request.body()
    success, msg = await store_report_data(session, user, data, file)
    status_code = 200 if success else 400
    return JSONResponse(
        status_code=status_code,
        content={"success": success, "message": msg},
    )


@api_router.post("/upload_parse")
async def handle_multiqc_data(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Parse uploaded MultiQC data."""
    json_data = await request.json()
    data = json_data.get("data")
    success, msg = await handle_report_data(session, user, data)
    status_code = 200 if success else 400
    return JSONResponse(
        status_code=status_code,
        content={"success": success, "message": msg},
    )


@api_router.post("/update_users")
async def admin_update_users(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_admin_user),
) -> JSONResponse:
    """Update user (admin only)."""
    data = await request.json()
    try:
        user_id = int(data["user_id"])
        data["user_id"] = user_id
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    cured_data = {key: (data[key] if data[key] != "None" else None) for key in data}

    try:
        form = AdminForm(**cured_data)
    except ValidationError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)},
        )

    result = await session.execute(select(User).where(User.user_id == user_id))
    target_user = result.scalar_one_or_none()
    if target_user:
        for key, value in cured_data.items():
            if hasattr(target_user, key):
                setattr(target_user, key, value)
        await session.commit()
    return JSONResponse(content={"success": True})


@api_router.post("/delete_users")
async def admin_delete_users(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_admin_user),
) -> JSONResponse:
    """Delete user (admin only)."""
    data = await request.json()
    try:
        user_id = int(data["user_id"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    result = await session.execute(select(User).where(User.user_id == user_id))
    target_user = result.scalar_one_or_none()
    if target_user:
        await session.delete(target_user)
        await session.commit()
    return JSONResponse(content={"success": True})


@api_router.post("/reset_password")
async def reset_password(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Reset user password."""
    data = await request.json()
    if user.is_admin or data.get("user_id") == user.user_id:
        new_password = user.reset_password()
        session.add(user)
        await session.commit()
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    return JSONResponse(content={"success": True, "password": new_password})


@api_router.post("/set_password")
async def set_password(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Set user password."""
    data = await request.json()
    user.set_password(data["password"])
    session.add(user)
    await session.commit()
    return JSONResponse(content={"success": True})


@api_router.post("/add_user")
async def admin_add_users(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_admin_user),
) -> JSONResponse:
    """Add new user (admin only)."""
    data = await request.json()
    try:
        data["user_id"] = int(data["user_id"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    new_user = User(**data)
    await new_user.enforce_admin_async(session)
    password = new_user.reset_password()
    new_user.active = True
    session.add(new_user)
    await session.commit()
    return JSONResponse(
        content={"success": True, "password": password, "api_token": user.api_token}
    )


@api_router.post("/get_samples_per_report")
async def get_samples_per_report(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get samples for a report."""
    data = await request.json()
    report_id = data.get("report_id")
    result = await session.execute(
        select(distinct(PlotData.sample_name), Report.title)
        .join(Report)
        .where(PlotData.report_id == report_id)
    )
    sample_names = {x[0]: x[1] for x in result.all()}
    return JSONResponse(content=sample_names)


@api_router.post("/get_report_plot")
async def get_report_plot(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get report plot."""
    data = await request.json()
    plot_type = data.get("plot_type")
    filters = data.get("filters", [])
    sample_names = await get_samples(session, filters)
    html = await generate_report_plot(session, plot_type, sample_names)
    return JSONResponse(content={"success": True, "plot": html})


@api_router.post("/count_samples")
async def count_samples(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Count samples matching filters."""
    data = await request.json()
    filters = data.get("filters", [])
    count = await get_samples(session, filters, count=True)
    return JSONResponse(content={"success": True, "count": count})


@api_router.api_route("/report_filter_fields", methods=["GET", "POST"])
async def report_filter_fields(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get report filter fields."""
    data = await request.json() if request.method == "POST" else {}
    filters = get_filter_from_data(data)
    return_data = await aggregate_new_parameters(session, user, filters, True)
    return JSONResponse(
        content={
            "success": True,
            "num_samples": return_data[0],
            "report_plot_types": return_data[1],
        }
    )


@api_router.api_route("/get_sample_meta_fields", methods=["GET", "POST"])
async def get_sample_meta_fields(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get sample metadata fields."""
    data = await request.json() if request.method == "POST" else {}
    filters = get_filter_from_data(data)
    return_data = await aggregate_new_parameters(session, user, filters, False)
    return JSONResponse(
        content={
            "success": True,
            "num_samples": return_data[0],
            "sample_meta_fields": return_data[2],
        }
    )


@api_router.post("/save_filters")
async def save_filters(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Save sample filters."""
    data = await request.json()
    one_filter = data.get("filters", [])
    meta = data.get("meta", {})
    filter_data = json.dumps(one_filter)
    if one_filter and meta:
        new_sf = SampleFilter(
            sample_filter_name=meta.get("name"),
            sample_filter_tag=meta.get("set"),
            is_public=meta.get("is_public", False),
            sample_filter_data=filter_data,
            user_id=user.user_id,
        )
        session.add(new_sf)
        await session.commit()
        await session.refresh(new_sf)
        return JSONResponse(
            content={
                "success": True,
                "message": "Filters created successfully",
                "filter_id": new_sf.sample_filter_id,
            }
        )
    else:
        return JSONResponse(
            content={"success": False, "message": "Filters or metadata were empty"}
        )


@api_router.api_route("/get_filters", methods=["GET", "POST"])
async def get_filters(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get user filters."""
    data = await get_user_filters(session, user)
    return JSONResponse(content={"success": True, "data": data})


@api_router.api_route("/update_favourite_plot", methods=["GET", "POST"])
async def update_favourite_plot(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Update favourite plot."""
    data = await request.json()
    plot_info = data.get("plot_id", "").split(" -- ")
    method = data.get("method", None)
    if plot_info and method:
        try:
            await update_fav_report_plot_type(session, method, user, plot_info)
        except Exception as e:
            return JSONResponse(content={"success": False, "message": str(e)})
    return JSONResponse(content={"success": True})


@api_router.post("/get_sample_data")
async def get_sample_data(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get sample data."""
    data = await request.json()
    my_filters = get_filter_from_data(data)
    data_keys = data.get("fields", {})
    ret_data = await get_sample_fields_values(session, data_keys, my_filters)
    return JSONResponse(content=ret_data)


@api_router.post("/get_distribution_plot")
async def get_distribution_plot(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get distribution plot."""
    data = await request.json()
    my_filters = get_filter_from_data(data)
    data_keys = data.get("fields", {})
    nbins = data.get("nbins", 20)
    ptype = data.get("ptype", 20)
    plot_data = await get_sample_fields_values(session, data_keys, my_filters)
    html = generate_distribution_plot(plot_data, nbins, ptype)
    return JSONResponse(content={"success": True, "plot": html})


@api_router.post("/get_trend_plot")
async def get_trend_plot(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get trend plot."""
    data = await request.json()
    my_filters = get_filter_from_data(data)
    data_keys = data.get("fields", {})
    plot_data = await get_timeline_sample_data(session, my_filters, data_keys)
    html = generate_trend_plot(plot_data)
    return JSONResponse(content={"success": True, "plot": html})


@api_router.post("/get_comparison_plot")
async def get_comparison_plot(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get comparison plot."""
    data = await request.json()
    my_filters = get_filter_from_data(data)
    data_keys = data.get("fields", {})
    field_names = data.get("field_names", {})
    pointsize = data.get("pointsize", 10)
    joinmarkers = data.get("joinmarkers", False)
    plot_data = await get_sample_fields_values(
        session, data_keys.values(), my_filters, num_fieldids=True
    )
    html = generate_comparison_plot(
        plot_data, data_keys, field_names, pointsize, joinmarkers
    )
    return JSONResponse(content={"success": True, "plot": html})


@api_router.post("/update_filters")
async def update_filters(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Update user filters."""
    data = await request.json()
    method = data.get("method")
    filter_id = float(data.get("filter_id"))
    filter_object = data.get("filters", {})
    await update_user_filter(session, user, method, filter_id, filter_object)
    return JSONResponse(content={"success": True})


@api_router.post("/get_timeline_sample_data")
async def timeline_sample_data(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get timeline sample data."""
    data = await request.json()
    my_filters = get_filter_from_data(data)
    data_keys = data.get("fields", {})
    ret_data = await get_timeline_sample_data(session, my_filters, data_keys)
    return JSONResponse(content=ret_data)


@api_router.api_route("/get_reports", methods=["GET", "POST"])
async def get_reports(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get reports."""
    count = False
    filtering = None
    if request.method == "POST":
        data = await request.json()
        filtering = (data.get("key"), data.get("value"))
        if filtering[1] == "":
            filtering = None
    if not user.is_admin:
        user_id = user.user_id
    else:
        user_id = None
    ret_data = await get_reports_data(session, count=count, user_id=user_id, filters=filtering)
    return JSONResponse(content=ret_data)


@api_router.post("/delete_report")
async def delete_report(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Delete a report."""
    data = await request.json()
    await delete_report_data(session, data.get("report_id", -1))
    return JSONResponse(content={"success": True})


@api_router.post("/get_favourite_plot")
async def get_favourite_plot(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get favourite plot data."""
    data = await request.json()
    favourite_id = data.get("favourite_id")
    plot_results = await get_favourite_plot_data(session, user, favourite_id)
    plot_results["success"] = True
    return JSONResponse(content=plot_results)


@api_router.post("/save_plot_favourite")
async def save_plot_favourite(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Save a plot as favourite."""
    data = await request.json()
    plot_type = data.get("type")
    request_data = data.get("request_data")
    title = data.get("title")
    description = data.get("description")
    pf_id = await save_plot_favourite_data(session, user, plot_type, request_data, title, description)
    return JSONResponse(content={"favourite_id": pf_id, "success": True})


@api_router.post("/delete_plot_favourite")
async def delete_plot_favourite(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Delete a favourite plot."""
    data = await request.json()
    favourite_id = data.get("favourite_id")
    result = await session.execute(
        select(PlotFavourite).where(
            PlotFavourite.user_id == user.user_id,
            PlotFavourite.plot_favourite_id == favourite_id,
        )
    )
    plot_fav = result.scalar_one_or_none()
    if plot_fav:
        await session.delete(plot_fav)
        await session.commit()
    return JSONResponse(content={"success": True})


@api_router.post("/get_dashboard")
async def get_dashboard(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Get dashboard data."""
    data = await request.json()
    dashboard_id = data.get("dashboard_id")
    results = await get_dashboard_data(session, user, dashboard_id)
    results["success"] = True
    return JSONResponse(content=results)


@api_router.post("/save_dashboard")
async def save_dashboard(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Save a dashboard."""
    data = await request.json()
    title = data.get("title")
    request_data = data.get("data")
    is_public = data.get("is_public", False)
    dash_id = await save_dashboard_data(session, user, title, request_data, is_public)
    return JSONResponse(content={"dashboard_id": dash_id, "success": True})


@api_router.post("/delete_dashboard")
async def delete_dashboard(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Delete a dashboard."""
    data = await request.json()
    dashboard_id = data.get("dashboard_id")
    result = await session.execute(
        select(Dashboard).where(
            Dashboard.user_id == user.user_id,
            Dashboard.dashboard_id == dashboard_id,
        )
    )
    dashboard = result.scalar_one_or_none()
    if dashboard:
        await session.delete(dashboard)
        await session.commit()
    return JSONResponse(content={"success": True})


@api_router.post("/count_queued_uploads")
async def count_queued_uploads(
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    """Count queued uploads."""
    count = await get_queued_uploads(session, count=True)
    return JSONResponse(content={"success": True, "count": count})
