from django.urls import path

from .views import signup_disabled

urlpatterns = [
    # Override the signup URL to show disabled message
    path("signup/", signup_disabled, name="account_signup"),
]
