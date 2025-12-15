from django.contrib import admin
from django.urls import include, path

from . import views

app_name = "omas"

urlpatterns = [
    # Omas Coffee home page
    path("", views.home, name="home"),
    # Admin (required for staff access)
    path("admin/", admin.site.urls),
    # Authentication (required for allauth)
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    # Utility URLs (for search, lighthouse, etc.)
    path("", include("utils.urls")),
]
