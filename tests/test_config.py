# -*- coding: utf-8 -*-
"""
Test configs.
"""
import pytest

from ultraqc.app import create_app
from ultraqc.settings import DevConfig, ProdConfig


def test_production_config():
    """
    Production config.
    """
    app = create_app(ProdConfig)
    # FastAPI stores settings in app.state.settings
    assert app.state.settings.ENV == "prod"
    assert app.state.settings.DEBUG is False


def test_dev_config():
    """
    Development config.
    """
    app = create_app(DevConfig)
    # FastAPI stores settings in app.state.settings
    assert app.state.settings.ENV == "dev"
    assert app.state.settings.DEBUG is True
