# -*- coding: utf-8 -*-
"""
Helper utilities and decorators.
"""
from typing import List, Tuple


def get_form_errors(form) -> List[Tuple[str, str]]:
    """
    Get all errors from a Pydantic model or form.

    Returns a list of (field_name, error_message) tuples.
    """
    errors = []
    if hasattr(form, "errors"):
        # Pydantic ValidationError
        for error in form.errors():
            field = error.get("loc", ["unknown"])[-1]
            msg = error.get("msg", "Invalid value")
            errors.append((str(field), msg))
    return errors


def format_flash_errors(errors: List[Tuple[str, str]], category: str = "warning") -> List[Tuple[str, str]]:
    """
    Format errors for flash messages.

    Returns a list of (category, message) tuples.
    """
    return [(category, f"{field} - {error}") for field, error in errors]
