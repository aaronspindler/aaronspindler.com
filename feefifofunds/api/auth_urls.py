"""
Authentication API URLs.

Implements FUND-028: JWT authentication endpoints.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .authentication import CustomTokenObtainPairView, auth_status, current_user, logout

app_name = "auth"

urlpatterns = [
    # JWT Token endpoints
    path("token/", CustomTokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    # User endpoints
    path("me/", current_user, name="current-user"),
    path("status/", auth_status, name="auth-status"),
    path("logout/", logout, name="logout"),
]
