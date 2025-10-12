from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.urls import reverse


class NoSignupAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter that disables signup and redirects to login page
    """
    
    def is_open_for_signup(self, request):
        """
        Returns False to disable signup
        """
        return getattr(settings, 'ACCOUNT_ALLOW_REGISTRATION', True)
    
    def get_signup_redirect_url(self, request):
        """
        Redirect to login page if someone tries to access signup
        """
        return reverse('account_login')
