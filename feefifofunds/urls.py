from django.urls import path

from . import views

app_name = "feefifofunds"

urlpatterns = [
    # Main pages
    path("", views.fund_list, name="fund_list"),
    path("funds/", views.fund_list, name="fund_list_alt"),
    path("funds/<slug:slug>/", views.fund_detail, name="fund_detail"),
    path("compare/", views.compare_funds, name="compare"),
    # API endpoints
    path("api/search/", views.search_funds, name="search_funds"),
    path("api/calculate/", views.calculate_fee_impact, name="calculate_fee_impact"),
]
