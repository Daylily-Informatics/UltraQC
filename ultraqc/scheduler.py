# -*- coding: utf-8 -*-
"""
Background scheduler for UltraQC.

Uses APScheduler for background task processing.
"""

import asyncio
import datetime
import gzip
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
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ultraqc.model.models import Upload
from ultraqc.user.models import User

logger = logging.getLogger(__name__)


async def handle_report_data_async(
    session: AsyncSession, user: User, report_data: dict
) -> tuple[bool, str]:
    """
    Async version of handle_report_data.

    This is a placeholder that needs to be fully implemented.
    For now, it returns a success message.

    TODO: Implement full async report data handling.
    """
    logger.warning("handle_report_data_async is not fully implemented yet")
    return (True, "Report data handling placeholder - not fully implemented")

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
