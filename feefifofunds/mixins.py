"""
Custom mixins for FeeFiFoFunds views.

Provides access control and permission checking for class-based views.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class SuperuserRequiredMixin(LoginRequiredMixin):
    """
    Mixin to restrict class-based view access to superusers only.

    Usage:
        class MyView(SuperuserRequiredMixin, ListView):
            model = Fund
            ...
    """

    def dispatch(self, request, *args, **kwargs):
        """Check if user is superuser before dispatching request."""
        # First ensure user is logged in (from LoginRequiredMixin)
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Then check if user is superuser
        if not request.user.is_superuser:
            raise PermissionDenied("Access denied. Superuser privileges required.")

        return super().dispatch(request, *args, **kwargs)
