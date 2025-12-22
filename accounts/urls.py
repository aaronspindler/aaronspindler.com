from django.urls import path

from .views import signup_disabled

urlpatterns = [
    path("signup/", signup_disabled, name="account_signup"),
]
