"""
Comprehensive test suite for the accounts app.

This module serves as a central import point for all account tests,
making it easy to run the complete test suite or understand test coverage.

Test Coverage:
- Models: CustomUser model and its methods
- Forms: CustomUserCreationForm and CustomUserChangeForm
- Views: signup_disabled view and its behavior
- URLs: URL routing and resolution
- Admin: CustomUserAdmin configuration and functionality
- Adapters: NoSignupAccountAdapter for registration control
- Integration: Full authentication flow and system integration

To run all accounts tests:
    python manage.py test accounts

To run specific test modules:
    python manage.py test accounts.tests.test_models
    python manage.py test accounts.tests.test_forms
    python manage.py test accounts.tests.test_views
    python manage.py test accounts.tests.test_urls
    python manage.py test accounts.tests.test_admin
    python manage.py test accounts.tests.test_adapters
    python manage.py test accounts.tests.test_integration

To run with coverage:
    coverage run --source='accounts' manage.py test accounts
    coverage report
    coverage html
"""

# Import all test modules to ensure they're discovered
from .test_adapters import *
from .test_admin import *
from .test_forms import *
from .test_integration import *
from .test_models import *
from .test_urls import *
from .test_views import *

# Test Statistics Summary
TEST_COVERAGE_SUMMARY = {
    "models": {
        "CustomUser": [
            "user creation",
            "superuser creation",
            "string representation",
            "full name methods",
            "permissions",
            "duplicate username prevention",
        ]
    },
    "forms": {
        "CustomUserCreationForm": [
            "field validation",
            "password matching",
            "password strength",
            "duplicate username handling",
            "email validation",
            "user creation",
        ],
        "CustomUserChangeForm": [
            "field updates",
            "email changes",
            "username changes",
            "duplicate prevention on update",
        ],
    },
    "views": {
        "signup_disabled": [
            "redirect to login",
            "informative messaging",
            "POST request handling",
            "message persistence",
        ]
    },
    "urls": [
        "URL resolution",
        "view mapping",
        "redirect targets",
        "integration with allauth URLs",
    ],
    "admin": [
        "registration in admin",
        "custom forms usage",
        "list display configuration",
        "CRUD operations",
        "permissions and access control",
        "search functionality",
    ],
    "adapters": {
        "NoSignupAccountAdapter": [
            "signup control via settings",
            "redirect behavior",
            "inheritance from DefaultAccountAdapter",
        ]
    },
    "integration": [
        "full authentication flow",
        "registration blocking",
        "permission system",
        "password hashing",
        "session management",
        "user updates",
        "database constraints",
    ],
}


def get_test_count():
    """
    Get the total number of test methods in the accounts app.
    """
    import inspect
    import sys
    import unittest

    test_count = 0
    current_module = sys.modules[__name__]

    for name, obj in inspect.getmembers(current_module):
        if inspect.isclass(obj) and issubclass(obj, unittest.TestCase):
            # Count test methods (those starting with 'test_')
            test_methods = [m for m in dir(obj) if m.startswith("test_")]
            test_count += len(test_methods)

    return test_count


# Optional: Add custom test suite if needed
def suite():
    """
    Create a test suite for the accounts app.
    This can be used to customize test ordering or selection.
    """
    import unittest

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test modules in preferred order
    suite.addTests(loader.loadTestsFromModule(test_models))
    suite.addTests(loader.loadTestsFromModule(test_forms))
    suite.addTests(loader.loadTestsFromModule(test_views))
    suite.addTests(loader.loadTestsFromModule(test_urls))
    suite.addTests(loader.loadTestsFromModule(test_admin))
    suite.addTests(loader.loadTestsFromModule(test_adapters))
    suite.addTests(loader.loadTestsFromModule(test_integration))

    return suite
