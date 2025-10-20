#!/usr/bin/env python
"""Test script to verify domain routing works correctly.

This script simulates requests to different domains and verifies
that the correct URL configuration is being used.
"""

import os
import sys

import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import RequestFactory  # noqa: E402

from config.domain_routing import DomainRoutingMiddleware  # noqa: E402


def test_domain_routing():
    """Test that domain routing middleware works correctly."""
    factory = RequestFactory()

    # Create a simple get_response function
    def get_response(request):
        from django.http import HttpResponse

        return HttpResponse("OK")

    middleware = DomainRoutingMiddleware(get_response)

    # Test cases
    test_cases = [
        ("omas.coffee", "omas.urls", "Omas Coffee domain"),
        ("www.omas.coffee", "omas.urls", "Omas Coffee www subdomain"),
        ("aaronspindler.com", None, "Main site (no urlconf override)"),
        ("www.aaronspindler.com", None, "Main site www subdomain"),
        ("localhost", None, "Localhost (development)"),
    ]

    print("Testing Domain Routing Middleware")
    print("=" * 60)

    all_passed = True

    for host, expected_urlconf, description in test_cases:
        request = factory.get("/", HTTP_HOST=host)
        middleware(request)

        actual_urlconf = getattr(request, "urlconf", None)

        if actual_urlconf == expected_urlconf:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
            all_passed = False

        print(f"\n{status} - {description}")
        print(f"   Host: {host}")
        print(f"   Expected URLconf: {expected_urlconf or 'default (config.urls)'}")
        print(f"   Actual URLconf: {actual_urlconf or 'default (config.urls)'}")

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(test_domain_routing())
