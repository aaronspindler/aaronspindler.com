from django.urls import path

from . import views

app_name = "feefifofunds"

urlpatterns = [
    # Home
    path("", views.home, name="home"),
    # Fund list (FUND-033)
    path("funds/", views.FundListView.as_view(), name="fund-list"),
    # Fund detail (FUND-034)
    path("funds/<slug:slug>/", views.FundDetailView.as_view(), name="fund-detail"),
    # Comparison tool (FUND-035)
    path("compare/", views.compare_view, name="compare"),
]