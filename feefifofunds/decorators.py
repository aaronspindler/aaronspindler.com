"""
Custom decorators for FeeFiFoFunds views.

Provides access control and permission checking.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse


def superuser_required(view_func=None, json_response=False):
    """
    Decorator to restrict view access to superusers only.

    Args:
        view_func: The view function to wrap
        json_response: If True, return JSON error instead of raising PermissionDenied

    Usage:
        @superuser_required
        def my_view(request):
            ...

        @superuser_required(json_response=True)
        def my_api_view(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_superuser:
                if json_response:
                    return JsonResponse({"error": "Access denied. Superuser privileges required."}, status=403)
                else:
                    raise PermissionDenied("Access denied. Superuser privileges required.")
            return view_func(request, *args, **kwargs)

        return wrapped_view

    # Allow decorator to be used with or without parentheses
    if view_func is None:
        # Called with arguments: @superuser_required(json_response=True)
        return decorator
    else:
        # Called without arguments: @superuser_required
        return decorator(view_func)
