"""
URL configuration for FeeFiFoFunds.

Implements:
- FUND-024: Fund JSON API Endpoints (for AJAX, charts, etc.)
- FUND-025: Comparison JSON endpoint
- FUND-032: Base Templates routing (HTML views)
"""

from django.urls import path

from . import views, views_comparison, views_json

app_name = "feefifofunds"

urlpatterns = [
    # HTML views (FUND-032)
    path("", views.home, name="home"),
    path("funds/", views.FundListView.as_view(), name="fund-list"),
    path("funds/<slug:slug>/", views.FundDetailView.as_view(), name="fund-detail"),
    path("compare/", views.compare_view, name="compare"),
    # JSON API endpoints (FUND-024 - for AJAX, charts, etc.)
    path("api/funds/", views_json.fund_list_json, name="fund-list-json"),
    path("api/funds/<slug:slug>/", views_json.fund_detail_json, name="fund-detail-json"),
    path("api/funds/<slug:slug>/performance/", views_json.fund_performance_json, name="fund-performance-json"),
    path("api/funds/<slug:slug>/holdings/", views_json.fund_holdings_json, name="fund-holdings-json"),
    # Comparison endpoint (FUND-025)
    path("api/compare/", views_comparison.compare_funds_json, name="compare-json"),
]
