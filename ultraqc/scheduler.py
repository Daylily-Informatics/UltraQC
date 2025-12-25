# -*- coding: utf-8 -*-
"""
Background scheduler for UltraQC.

Uses APScheduler for background task processing.
"""

import asyncio
import datetime
import gzip
import hashlib
import io
import json
import logging
import os
import traceback
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ultraqc.model.models import (
    PlotCategory,
    PlotConfig,
    PlotData,
    Report,
    ReportMeta,
    Sample,
    SampleData,
    SampleDataType,
    Upload,
)
from ultraqc.user.models import User

logger = logging.getLogger(__name__)


def generate_hash(report_data: dict) -> str:
    """Generate MD5 hash of report data."""
    return hashlib.md5(json.dumps(report_data, sort_keys=True).encode()).hexdigest()


async def handle_report_data_async(
    session: AsyncSession, user: User, report_data: dict
) -> tuple[bool, str]:
    """
    Async version of handle_report_data.

    Parses MultiQC JSON data and saves it to the database.
    """
    if "data" in report_data:
        report_data = report_data["data"]
    report_hash = generate_hash(report_data)

    # Check that we don't already have a data file with this md5hash
    result = await session.execute(
        select(Report).where(Report.report_hash == report_hash)
    )
    if result.scalar_one_or_none():
        return (False, "Report already uploaded")

    # Pull the creation date if we can
    try:
        report_created_at = datetime.datetime.strptime(
            report_data["config_creation_date"], "%Y-%m-%d, %H:%M"
        )
    except Exception:
        report_created_at = datetime.datetime.now()

    # Add to the main report table
    new_report = Report(
        report_hash=report_hash, user_id=user.user_id, created_at=report_created_at
    )
    try:
        session.add(new_report)
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return (False, "Report already processed")

    logger.info(f"Created new report {new_report.report_id} from {user.email}")
    report_id = new_report.report_id

    # Save the user as a report meta value
    user_report_meta = ReportMeta(
        report_meta_key="username", report_meta_value=user.username, report_id=report_id
    )
    session.add(user_report_meta)

    # Get top-level `config_` JSON keys (strings only)
    new_meta_cnt = 0
    for key in report_data:
        if (
            key.startswith("config")
            and not isinstance(report_data[key], list)
            and not isinstance(report_data[key], dict)
            and report_data[key]
        ):
            new_meta_cnt += 1
            new_meta = ReportMeta(
                report_meta_key=key,
                report_meta_value=str(report_data[key]),
                report_id=report_id,
            )
            session.add(new_meta)
    logger.info(f"Wrote {new_meta_cnt} metadata fields for report {report_id}")

    # Save the raw parsed data (stuff that ends up in the multiqc_data directory)
    new_samp_cnt = 0
    sample_cache = {}  # Cache samples by name
    data_type_cache = {}  # Cache data types by data_id

    for s_key in report_data.get("report_saved_raw_data", {}):
        section = s_key.replace("multiqc_", "")
        # Go through each sample
        for s_name in report_data["report_saved_raw_data"][s_key]:
            new_samp_cnt += 1

            # Check cache first, then database
            if s_name in sample_cache:
                sample_id = sample_cache[s_name]
            else:
                result = await session.execute(
                    select(Sample).where(Sample.sample_name == s_name)
                )
                report_sample = result.scalar_one_or_none()
                if not report_sample:
                    report_sample = Sample(sample_name=s_name, report_id=report_id)
                    session.add(report_sample)
                    await session.flush()
                sample_id = report_sample.sample_id
                sample_cache[s_name] = sample_id

            # Go through each data key
            for d_key in report_data["report_saved_raw_data"][s_key][s_name]:
                # Check cache first
                if d_key in data_type_cache:
                    type_id = data_type_cache[d_key]
                else:
                    result = await session.execute(
                        select(SampleDataType).where(SampleDataType.data_id == d_key)
                    )
                    key_type = result.scalar_one_or_none()
                    if not key_type:
                        key_type = SampleDataType(
                            data_key=f"{section}__{d_key}",
                            data_section=section,
                            data_id=d_key,
                        )
                        session.add(key_type)
                        await session.flush()
                    type_id = key_type.sample_data_type_id
                    data_type_cache[d_key] = type_id

                # Save the data value
                value = report_data["report_saved_raw_data"][s_key][s_name][d_key]
                new_data = SampleData(
                    report_id=report_id,
                    sample_data_type_id=type_id,
                    sample_id=sample_id,
                    value=str(value),
                )
                session.add(new_data)

    logger.info(f"Wrote {new_samp_cnt} samples for report {report_id}")

    # Save report plot data and configs
    new_plotcfg_cnt = 0
    new_plotdata_cnt = 0
    plot_config_cache = {}
    category_cache = {}

    for plot in report_data.get("report_plot_data", {}):
        # Skip custom plots
        if "mqc_hcplot_" in plot:
            continue
        # Only support bar_graph and xy_line for now
        plot_type = report_data["report_plot_data"][plot].get("plot_type")
        if plot_type not in ["bar_graph", "xy_line"]:
            continue

        config_json = json.dumps(report_data["report_plot_data"][plot].get("config", {}))

        for dst_idx, dataset in enumerate(
            report_data["report_plot_data"][plot].get("datasets", [])
        ):
            # Get dataset name
            try:
                data_labels = report_data["report_plot_data"][plot]["config"].get("data_labels", [])
                if dst_idx < len(data_labels):
                    label = data_labels[dst_idx]
                    if isinstance(label, dict):
                        dataset_name = label.get("ylab", label.get("name", plot))
                    else:
                        dataset_name = str(label)
                else:
                    dataset_name = report_data["report_plot_data"][plot]["config"].get(
                        "ylab", report_data["report_plot_data"][plot]["config"].get("title", plot)
                    )
            except (KeyError, IndexError):
                dataset_name = plot

            # Get or create plot config
            cache_key = (plot_type, plot, dataset_name)
            if cache_key in plot_config_cache:
                config_id = plot_config_cache[cache_key]
            else:
                result = await session.execute(
                    select(PlotConfig).where(
                        PlotConfig.config_type == plot_type,
                        PlotConfig.config_name == plot,
                        PlotConfig.config_dataset == dataset_name,
                    )
                )
                plot_config = result.scalar_one_or_none()
                if not plot_config:
                    plot_config = PlotConfig(
                        config_type=plot_type,
                        config_name=plot,
                        config_dataset=dataset_name,
                        data=config_json,
                    )
                    session.add(plot_config)
                    await session.flush()
                    new_plotcfg_cnt += 1
                config_id = plot_config.config_id
                plot_config_cache[cache_key] = config_id

            # Process based on plot type
            if plot_type == "bar_graph":
                await _process_bar_graph_data(
                    session, report_data, plot, dst_idx, dataset, report_id,
                    config_id, sample_cache, category_cache
                )
                new_plotdata_cnt += len(dataset)

            elif plot_type == "xy_line":
                await _process_xy_line_data(
                    session, report_data, plot, dst_idx, dataset, report_id,
                    config_id, sample_cache, category_cache
                )
                new_plotdata_cnt += len(dataset)

    logger.info(
        f"Wrote plot data ({new_plotcfg_cnt} cfg, {new_plotdata_cnt} data points) for report {report_id}"
    )

    await session.commit()
    return (True, "Data upload successful")


async def _process_bar_graph_data(
    session: AsyncSession,
    report_data: dict,
    plot: str,
    dst_idx: int,
    dataset,  # Can be list or dict (new format)
    report_id: int,
    config_id: int,
    sample_cache: dict,
    category_cache: dict,
):
    """Process bar graph plot data - supports old and new MultiQC formats."""

    # New MultiQC format: dataset is a dict with 'samples' and 'cats' keys
    if isinstance(dataset, dict) and "cats" in dataset:
        sample_names = dataset.get("samples", [])
        categories = dataset.get("cats", [])

        for cat in categories:
            data_key = cat.get("name", "")
            cat_data = json.dumps({k: v for k, v in cat.items() if k != "data"})

            # Get or create category
            cat_cache_key = (config_id, data_key)
            if cat_cache_key in category_cache:
                category_id = category_cache[cat_cache_key]
            else:
                result = await session.execute(
                    select(PlotCategory).where(PlotCategory.category_name == data_key)
                )
                existing_category = result.scalar_one_or_none()
                if not existing_category:
                    existing_category = PlotCategory(
                        report_id=report_id,
                        config_id=config_id,
                        category_name=data_key,
                        data=cat_data,
                    )
                    session.add(existing_category)
                    await session.flush()
                else:
                    existing_category.data = cat_data
                category_id = existing_category.plot_category_id
                category_cache[cat_cache_key] = category_id

            # Save data for each sample
            for sa_idx, actual_data in enumerate(cat.get("data", [])):
                if sa_idx < len(sample_names):
                    s_name = sample_names[sa_idx]
                else:
                    s_name = f"sample_{sa_idx}"

                # Get or create sample
                if s_name in sample_cache:
                    sample_id = sample_cache[s_name]
                else:
                    result = await session.execute(
                        select(Sample).where(Sample.sample_name == s_name)
                    )
                    existing_sample = result.scalar_one_or_none()
                    if existing_sample:
                        sample_id = existing_sample.sample_id
                    else:
                        new_sample = Sample(sample_name=s_name, report_id=report_id)
                        session.add(new_sample)
                        await session.flush()
                        sample_id = new_sample.sample_id
                    sample_cache[s_name] = sample_id

                new_dataset_row = PlotData(
                    report_id=report_id,
                    config_id=config_id,
                    sample_id=sample_id,
                    plot_category_id=category_id,
                    data=json.dumps(actual_data),
                )
                session.add(new_dataset_row)
        return

    # Old MultiQC format: dataset is a list of dicts
    if not isinstance(dataset, list):
        return

    for sub_dict in dataset:
        if not isinstance(sub_dict, dict):
            continue
        data_key = str(sub_dict.get("name", ""))
        data = json.dumps({x: y for x, y in list(sub_dict.items()) if x != "data"})

        # Get or create category
        cat_cache_key = (config_id, data_key)
        if cat_cache_key in category_cache:
            category_id = category_cache[cat_cache_key]
        else:
            result = await session.execute(
                select(PlotCategory).where(PlotCategory.category_name == data_key)
            )
            existing_category = result.scalar_one_or_none()
            if not existing_category:
                existing_category = PlotCategory(
                    report_id=report_id,
                    config_id=config_id,
                    category_name=data_key,
                    data=data,
                )
                session.add(existing_category)
                await session.flush()
            else:
                existing_category.data = data
            category_id = existing_category.plot_category_id
            category_cache[cat_cache_key] = category_id

        # Get sample names from plot data
        samples_list = report_data["report_plot_data"][plot].get("samples", [[]])
        if dst_idx < len(samples_list):
            sample_names = samples_list[dst_idx]
        else:
            sample_names = []

        for sa_idx, actual_data in enumerate(sub_dict.get("data", [])):
            # Determine sample name
            if sa_idx < len(sample_names):
                s_name = sample_names[sa_idx]
            else:
                s_name = sub_dict.get("name", f"sample_{sa_idx}")

            # Get or create sample
            if s_name in sample_cache:
                sample_id = sample_cache[s_name]
            else:
                result = await session.execute(
                    select(Sample).where(Sample.sample_name == s_name)
                )
                existing_sample = result.scalar_one_or_none()
                if existing_sample:
                    sample_id = existing_sample.sample_id
                else:
                    new_sample = Sample(sample_name=s_name, report_id=report_id)
                    session.add(new_sample)
                    await session.flush()
                    sample_id = new_sample.sample_id
                sample_cache[s_name] = sample_id

            new_dataset_row = PlotData(
                report_id=report_id,
                config_id=config_id,
                sample_id=sample_id,
                plot_category_id=category_id,
                data=json.dumps(actual_data),
            )
            session.add(new_dataset_row)


async def _process_xy_line_data(
    session: AsyncSession,
    report_data: dict,
    plot: str,
    dst_idx: int,
    dataset,  # Can be list or dict (new format)
    report_id: int,
    config_id: int,
    sample_cache: dict,
    category_cache: dict,
):
    """Process xy_line plot data - supports old and new MultiQC formats."""

    # Get category name from config
    try:
        data_labels = report_data["report_plot_data"][plot].get("config", {}).get("data_labels", [])
        if dst_idx < len(data_labels):
            label = data_labels[dst_idx]
            if isinstance(label, dict):
                data_key = label.get("ylab", label.get("name", plot))
            else:
                data_key = str(label)
        else:
            config = report_data["report_plot_data"][plot].get("config", {})
            data_key = config.get("ylab", config.get("title", plot))
    except (KeyError, TypeError):
        data_key = plot

    # New MultiQC format: dataset is a dict with 'lines' key
    if isinstance(dataset, dict) and "lines" in dataset:
        lines = dataset.get("lines", [])

        for line in lines:
            s_name = line.get("name", f"sample_{dst_idx}")
            line_data = json.dumps({k: v for k, v in line.items() if k != "pairs"})

            # Get or create category
            cat_cache_key = (config_id, data_key)
            if cat_cache_key in category_cache:
                category_id = category_cache[cat_cache_key]
            else:
                result = await session.execute(
                    select(PlotCategory).where(PlotCategory.category_name == data_key)
                )
                existing_category = result.scalar_one_or_none()
                if not existing_category:
                    existing_category = PlotCategory(
                        report_id=report_id,
                        config_id=config_id,
                        category_name=data_key,
                        data=line_data,
                    )
                    session.add(existing_category)
                    await session.flush()
                else:
                    existing_category.data = line_data
                category_id = existing_category.plot_category_id
                category_cache[cat_cache_key] = category_id

            # Get or create sample
            if s_name in sample_cache:
                sample_id = sample_cache[s_name]
            else:
                result = await session.execute(
                    select(Sample).where(Sample.sample_name == s_name)
                )
                sample = result.scalar_one_or_none()
                if not sample:
                    sample = Sample(sample_name=s_name, report_id=report_id)
                    session.add(sample)
                    await session.flush()
                    sample_id = sample.sample_id
                else:
                    sample_id = sample.sample_id
                sample_cache[s_name] = sample_id

            new_dataset_row = PlotData(
                report_id=report_id,
                config_id=config_id,
                sample_id=sample_id,
                plot_category_id=category_id,
                data=json.dumps(line.get("pairs", [])),
            )
            session.add(new_dataset_row)
        return

    # Old MultiQC format: dataset is a list
    if not isinstance(dataset, list):
        return

    for sub_dict in dataset:
        if not isinstance(sub_dict, dict):
            continue

        data = json.dumps({x: y for x, y in list(sub_dict.items()) if x != "data"})

        # Get or create category
        cat_cache_key = (config_id, data_key)
        if cat_cache_key in category_cache:
            category_id = category_cache[cat_cache_key]
        else:
            result = await session.execute(
                select(PlotCategory).where(PlotCategory.category_name == data_key)
            )
            existing_category = result.scalar_one_or_none()
            if not existing_category:
                existing_category = PlotCategory(
                    report_id=report_id,
                    config_id=config_id,
                    category_name=data_key,
                    data=data,
                )
                session.add(existing_category)
                await session.flush()
            else:
                existing_category.data = data
            category_id = existing_category.plot_category_id
            category_cache[cat_cache_key] = category_id

        # Get sample name
        s_name = sub_dict.get("name", f"sample_{dst_idx}")

        # Get or create sample
        if s_name in sample_cache:
            sample_id = sample_cache[s_name]
        else:
            result = await session.execute(
                select(Sample).where(Sample.sample_name == s_name)
            )
            sample = result.scalar_one_or_none()
            if not sample:
                sample = Sample(sample_name=s_name, report_id=report_id)
                session.add(sample)
                await session.flush()
                sample_id = sample.sample_id
            else:
                sample_id = sample.sample_id
            sample_cache[s_name] = sample_id

        new_dataset_row = PlotData(
            report_id=report_id,
            config_id=config_id,
            sample_id=sample_id,
            plot_category_id=category_id,
            data=json.dumps(sub_dict.get("data", [])),
        )
        session.add(new_dataset_row)


# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None
_async_session_factory: Optional[sessionmaker] = None


def init_scheduler(app, database_url: str):
    """Initialize the scheduler with the FastAPI app."""
    global scheduler, _async_session_factory

    if scheduler is not None and scheduler.running:
        return

    # Create async engine for scheduler
    async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    async_url = async_url.replace("sqlite://", "sqlite+aiosqlite://")
    engine = create_async_engine(async_url, echo=False)
    _async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        upload_reports_job,
        trigger=IntervalTrigger(seconds=30),
        id="upload_reports",
        name="Process queued report uploads",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    global scheduler
    if scheduler is not None and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shutdown")


async def get_scheduler_session() -> AsyncSession:
    """Get an async session for the scheduler."""
    if _async_session_factory is None:
        raise RuntimeError("Scheduler not initialized")
    async with _async_session_factory() as session:
        yield session


async def upload_reports_job():
    """Process queued report uploads."""
    if _async_session_factory is None:
        logger.warning("Scheduler session factory not initialized")
        return

    async with _async_session_factory() as session:
        try:
            # Get queued uploads
            result = await session.execute(
                select(Upload).where(Upload.status == "NOT TREATED")
            )
            queued_uploads = result.scalars().all()

            for row in queued_uploads:
                # Get the user
                user_result = await session.execute(
                    select(User).where(User.user_id == row.user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    logger.error(f"User not found for upload {row.upload_id}")
                    continue

                logger.info(
                    f"Beginning process of upload #{row.upload_id} from {user.email}"
                )

                row.status = "IN TREATMENT"
                session.add(row)
                await session.commit()

                # Check if we have a gzipped file
                gzipped = False
                with open(row.path, "rb") as fh:
                    file_start = fh.read(3)
                    if file_start == b"\x1f\x8b\x08":
                        gzipped = True

                try:
                    if gzipped:
                        with io.BufferedReader(gzip.open(row.path, "rb")) as fh:
                            raw_data = fh.read().decode("utf-8")
                    else:
                        with io.open(row.path, "rb") as fh:
                            raw_data = fh.read().decode("utf-8")

                    data = json.loads(raw_data)
                    # Now save the parsed JSON data to the database
                    ret = await handle_report_data_async(session, user, data)
                except Exception:
                    ret = (
                        False,
                        f"<pre><code>{traceback.format_exc()}</code></pre>",
                    )
                    logger.error(
                        f"Error processing upload {row.upload_id}: {traceback.format_exc()}"
                    )

                if ret[0]:
                    row.status = "TREATED"
                    row.message = "The document has been uploaded successfully"
                    os.remove(row.path)
                else:
                    if ret[1] == "Report already processed":
                        logger.info(
                            f"Upload {row.upload_id} already being processed by another worker, skipping"
                        )
                        continue
                    row.status = "FAILED"
                    row.message = f"The document has not been uploaded : {ret[1]}"

                row.modified_at = datetime.datetime.utcnow()
                logger.info(
                    f"Finished processing upload #{row.upload_id} to state {row.status}"
                )
                session.add(row)
                await session.commit()

        except Exception as e:
            logger.error(f"Error in upload_reports_job: {e}")
