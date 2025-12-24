"""
Tests for filter functionality.
"""
import pytest

from ultraqc.model import models
from ultraqc.rest_api import schemas
from tests import factories


@pytest.fixture()
def report(session):
    r = factories.ReportFactory()
    session.add(r)
    session.commit()
    return r
