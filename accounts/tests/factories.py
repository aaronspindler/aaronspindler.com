"""
Test data factories for creating consistent fake user data across all tests.

This module provides factory functions to create test user instances with
consistent, realistic fake data that can be reused across all test files.
"""

import uuid

from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory:
    """Factory for creating test users with consistent data."""

    @staticmethod
    def create_user(username=None, email=None, password="testpass123", **kwargs):
        """Create a regular user with optional custom fields."""
        if not username:
            username = f"testuser_{uuid.uuid4().hex[:8]}"
        if email is None:
            email = f"{username}@example.com"

        return User.objects.create_user(username=username, email=email, password=password, **kwargs)

    @staticmethod
    def create_staff_user(username=None, email=None, password="testpass123", **kwargs):
        """Create a staff user with optional custom fields."""
        if not username:
            username = f"staff_{uuid.uuid4().hex[:8]}"
        if email is None:
            email = f"{username}@example.com"

        return User.objects.create_user(username=username, email=email, password=password, is_staff=True, **kwargs)

    @staticmethod
    def create_superuser(username=None, email=None, password="testpass123", **kwargs):
        """Create a superuser with optional custom fields."""
        if not username:
            username = f"admin_{uuid.uuid4().hex[:8]}"
        if email is None:
            email = f"{username}@example.com"

        return User.objects.create_superuser(username=username, email=email, password=password, **kwargs)

    @staticmethod
    def get_common_user_data():
        """Get common user data for form testing."""
        unique_id = uuid.uuid4().hex[:8]
        return {
            "username": f"testuser_{unique_id}",
            "email": f"test_{unique_id}@example.com",
            "password": "testpass123",
        }
