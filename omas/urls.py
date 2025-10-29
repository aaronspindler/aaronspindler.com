from django.urls import path

from . import views

app_name = "omas"

urlpatterns = [
    path("", views.home, name="home"),
]
