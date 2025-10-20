"""
API URL configuration for FeeFiFoFunds v1.

This module defines the URL routing for the FeeFiFoFunds REST API.
"""

from django.urls import path

from .views import HealthCheckView, api_root

app_name = "api"

urlpatterns = [
    # API Root
    path("", api_root, name="root"),
    # Health check
    path("health/", HealthCheckView.as_view(), name="health-check"),
    # Future endpoints will be added here as they're implemented:
    # - FUND-024: Fund list/detail endpoints
    # - FUND-025: Comparison API endpoints
    # - FUND-026: Search and filter API
    # - FUND-027: Analytics endpoints
    # - FUND-028: Authentication endpoints
]
