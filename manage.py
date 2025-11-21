#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    # SAFETY: Prevent running tests locally against production database
    if "test" in sys.argv and not os.environ.get("TESTING_IN_DOCKER"):
        print("\n" + "=" * 70)
        print("❌ ERROR: Running tests locally is NOT ALLOWED")
        print("=" * 70)
        print("\nThis project connects to PRODUCTION database in local development.")
        print("Tests MUST be run in Docker with isolated infrastructure.\n")
        print("Use one of these commands:")
        print("  make test                              # Run all tests")
        print("  make test-run-app APP=blog             # Run tests for specific app")
        print("  make test-run-specific TEST=blog.tests.test_models")
        print("\nFor local development:")
        print("  python manage.py runserver             # Development server")
        print("  python manage.py shell                 # Django shell")
        print("=" * 70 + "\n")
        sys.exit(1)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
