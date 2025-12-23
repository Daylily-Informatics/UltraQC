"""
Tests for plot-related API endpoints.

NOTE: These tests are being migrated from Flask to FastAPI.
"""
import json
from urllib.parse import urlencode

import pytest
from plotly.offline import plot

from tests import factories


@pytest.mark.asyncio
async def test_trend_data_measurement(db_session, client):
    """Test trend data endpoint with measurement statistic."""
    # Create 5 reports each with 1 sample. Each has a single field called 'test_field'
    data_type = factories.SampleDataTypeFactory.build()
    db_session.add(data_type)
    await db_session.commit()

    reports = factories.ReportFactory.build_batch(5)
    for report in reports:
        db_session.add(report)
    await db_session.commit()

    params = {
        "filter": json.dumps([]),
        "fields": json.dumps([data_type.data_key]),
        "statistic": "measurement",
        "statistic_options[center_line]": "mean",
    }
    url = f"/rest_api/v1/trend_data?{urlencode(params)}"
    response = await client.get(url, headers={"Content-Type": "application/json"})

    # Check the request was successful
    assert response.status_code == 200, f"Status code {response.status_code}"


@pytest.mark.asyncio
async def test_trend_data_iforest(db_session, client):
    """Test trend data endpoint with iforest statistic."""
    # Create 5 reports each with 1 sample. Each has a single field called 'test_field'
    data_type = factories.SampleDataTypeFactory.build()
    db_session.add(data_type)
    await db_session.commit()

    reports = factories.ReportFactory.build_batch(5)
    for report in reports:
        db_session.add(report)
    await db_session.commit()

    params = {
        "filter": json.dumps([]),
        "fields": json.dumps([data_type.data_key]),
        "statistic": "iforest",
        "statistic_options[contamination]": "0.01",
    }
    url = f"/rest_api/v1/trend_data?{urlencode(params)}"
    response = await client.get(url, headers={"Content-Type": "application/json"})

    # Check the request was successful
    assert response.status_code == 200, f"Status code {response.status_code}"
