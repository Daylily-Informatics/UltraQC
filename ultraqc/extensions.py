# -*- coding: utf-8 -*-
"""
Extensions module for FastAPI.

This module provides compatibility layers and shared utilities.
"""
from pathlib import Path
from typing import Optional

from marshmallow import Schema

# Migrations directory path
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


# Simple in-memory cache (can be replaced with Redis or other backends)
class SimpleCache:
    """Simple in-memory cache implementation."""

    def __init__(self):
        self._cache = {}

    def get(self, key: str):
        return self._cache.get(key)

    def set(self, key: str, value, timeout: Optional[int] = None):
        self._cache[key] = value

    def delete(self, key: str):
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()


cache = SimpleCache()


# Marshmallow for serialization
class MarshmallowExtension:
    """Wrapper for Marshmallow schemas."""

    def __init__(self):
        self.Schema = Schema


ma = MarshmallowExtension()
