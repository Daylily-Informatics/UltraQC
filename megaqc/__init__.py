# -*- coding: utf-8 -*-
"""
Main application package.
"""
try:
    from importlib.metadata import version as get_version
    version = get_version("megaqc")
except Exception:
    version = "0.0.0"
