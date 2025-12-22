from django.contrib import admin
from django.urls import include, path

from . import views

app_name = "omas"

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("", include("utils.urls")),
]
