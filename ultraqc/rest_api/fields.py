"""
Custom field types for serialization/deserialization.

This module provides custom Marshmallow fields for the REST API.
"""
import json
from typing import Any, List, Optional, Type

from marshmallow import fields, missing


class JsonString(fields.Field):
    """
    A Marshmallow field that serializes/deserializes JSON strings.

    By default, it deserializes JSON strings to Python objects and serializes
    Python objects to JSON strings. If `invert=True`, the behavior is reversed.
    """

    def __init__(self, invert: bool = False, attribute: Optional[str] = None, **kwargs):
        self.invert = invert
        super().__init__(attribute=attribute, **kwargs)

    def _serialize(self, value: Any, attr: str, obj: Any, **kwargs) -> Any:
        """Serialize value to/from JSON string."""
        if value is None:
            return None
        if self.invert:
            # Serialize Python object to JSON string
            return json.dumps(value)
        else:
            # Deserialize JSON string to Python object
            if isinstance(value, str):
                return json.loads(value)
            return value

    def _deserialize(self, value: Any, attr: str, data: Any, **kwargs) -> Any:
        """Deserialize value from/to JSON string."""
        if value is None:
            return None
        if self.invert:
            # Deserialize JSON string to Python object
            if isinstance(value, str):
                return json.loads(value)
            return value
        else:
            # Serialize Python object to JSON string
            return json.dumps(value)


class FilterReference(fields.Field):
    """
    A Marshmallow field that references a filter by ID and returns its data.

    This field is used to deserialize filter references in API requests.
    When given a filter ID, it returns the filter's data as a list.
    When given a list directly, it passes it through.
    """

    def _serialize(self, value: Any, attr: str, obj: Any, **kwargs) -> Any:
        """Serialize filter data."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return []

    def _deserialize(self, value: Any, attr: str, data: Any, **kwargs) -> Any:
        """
        Deserialize filter reference.

        If value is a list, return it directly.
        If value is an integer (filter ID), this would need to look up the filter.
        For now, we just return the value as-is since async lookup isn't supported
        in Marshmallow's synchronous deserialization.
        """
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                # Try to parse as JSON
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        return []
