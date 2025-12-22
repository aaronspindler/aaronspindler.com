from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.urls import reverse


class NoSignupAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def get_signup_redirect_url(self, request):
        return reverse("account_login")
