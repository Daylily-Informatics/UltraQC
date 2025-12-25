# -*- coding: utf-8 -*-
"""
Test forms.

Note: These tests were written for Flask-WTForms. With the migration to
FastAPI and Pydantic, form validation is now done via Pydantic models.
Pydantic validation happens at construction time, not via a validate() method.
Database-level validation (checking for existing users) is now done in the views.
"""
import pytest
from pydantic import ValidationError

from ultraqc.user.forms import RegisterForm
from tests.factories import UserFactory


@pytest.fixture()
def user_attrs():
    return UserFactory.build()


class TestRegisterForm:
    """
    Register form validation tests.

    Note: In the new architecture, database-level checks (like checking for
    existing usernames/emails) are done in the view layer, not the form.
    These tests focus on Pydantic validation.
    """

    def test_validate_success(self, user_attrs):
        """
        Register form validates successfully with valid data.
        """
        # Pydantic validates at construction time
        form = RegisterForm(
            username=user_attrs.username,
            email=user_attrs.email,
            first_name=user_attrs.first_name,
            last_name=user_attrs.last_name,
            password="password",
            confirm="password",
        )
        # If we get here without exception, validation passed
        assert form.username == user_attrs.username.strip()
        assert form.email == user_attrs.email

    def test_password_mismatch(self, user_attrs):
        """
        Test that mismatched passwords raise ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            RegisterForm(
                username=user_attrs.username,
                email=user_attrs.email,
                first_name=user_attrs.first_name,
                last_name=user_attrs.last_name,
                password="password1",
                confirm="password2",
            )
        assert "Passwords must match" in str(exc_info.value)

    def test_username_too_short(self, user_attrs):
        """
        Test that short usernames raise ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            RegisterForm(
                username="ab",  # Too short
                email=user_attrs.email,
                first_name=user_attrs.first_name,
                last_name=user_attrs.last_name,
                password="password",
                confirm="password",
            )
        assert "Username must be between 3 and 25 characters" in str(exc_info.value)

    def test_password_too_short(self, user_attrs):
        """
        Test that short passwords raise ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            RegisterForm(
                username=user_attrs.username,
                email=user_attrs.email,
                first_name=user_attrs.first_name,
                last_name=user_attrs.last_name,
                password="short",  # Too short
                confirm="short",
            )
        assert "Password must be between 6 and 40 characters" in str(exc_info.value)

    def test_invalid_email(self, user_attrs):
        """
        Test that invalid email addresses raise ValidationError.
        """
        with pytest.raises(ValidationError):
            RegisterForm(
                username=user_attrs.username,
                email="not-an-email",  # Invalid
                first_name=user_attrs.first_name,
                last_name=user_attrs.last_name,
                password="password",
                confirm="password",
            )
