"""
Tests for upload functionality.
"""
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select, func

from ultraqc.model import models
from tests import factories


@pytest_asyncio.fixture()
async def upload(db_session):
    r = factories.UploadFactory()
    db_session.add(r)
    await db_session.commit()
    await db_session.refresh(r)
    return r


@pytest.mark.asyncio
async def test_post_upload_list(db_session, client, token):
    """
    Test uploading a report.
    """
    result = await db_session.execute(select(func.count(models.Upload.upload_id)))
    count_1 = result.scalar()

    # Use importlib.resources to get the test data file
    test_data_path = Path(__file__).parent.parent / "multiqc_data.json"
    with open(test_data_path, "rb") as f:
        rv = await client.post(
            "/rest_api/v1/uploads",
            files={"report": ("multiqc_data.json", f, "application/json")},
            headers={
                "access_token": token,
            },
        )

    # Check the request was successful
    assert rv.status_code == 201, rv.json()

    # Check that there is a new Upload
    result = await db_session.execute(select(func.count(models.Upload.upload_id)))
    count_2 = result.scalar()
    assert count_2 == count_1 + 1
