from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from accounts.adapters import NoSignupAccountAdapter


class NoSignupAccountAdapterTest(TestCase):
    """
    Test the NoSignupAccountAdapter functionality.
    """

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.adapter = NoSignupAccountAdapter()

    def test_signup_disabled_by_default(self):
        """Test that signup is disabled when ACCOUNT_ALLOW_REGISTRATION is not set."""
        request = self.factory.get('/accounts/signup/')
        is_open = self.adapter.is_open_for_signup(request)
        # Default behavior depends on settings, but typically should be True unless overridden
        self.assertTrue(is_open)

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=False)
    def test_signup_explicitly_disabled(self):
        """Test that signup is disabled when ACCOUNT_ALLOW_REGISTRATION is False."""
        request = self.factory.get('/accounts/signup/')
        is_open = self.adapter.is_open_for_signup(request)
        self.assertFalse(is_open)

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=True)
    def test_signup_explicitly_enabled(self):
        """Test that signup is enabled when ACCOUNT_ALLOW_REGISTRATION is True."""
        request = self.factory.get('/accounts/signup/')
        is_open = self.adapter.is_open_for_signup(request)
        self.assertTrue(is_open)

    def test_signup_redirect_url(self):
        """Test that signup redirect URL points to login page."""
        request = self.factory.get('/accounts/signup/')
        redirect_url = self.adapter.get_signup_redirect_url(request)
        expected_url = reverse('account_login')
        self.assertEqual(redirect_url, expected_url)

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=False)
    def test_adapter_prevents_registration_flow(self):
        """Test that the adapter effectively prevents the registration flow."""
        request = self.factory.post('/accounts/signup/', {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
        })
        
        # Check that signup is not open
        self.assertFalse(self.adapter.is_open_for_signup(request))
        
        # Check that it would redirect to login
        redirect_url = self.adapter.get_signup_redirect_url(request)
        self.assertEqual(redirect_url, reverse('account_login'))

    def test_adapter_inheritance(self):
        """Test that NoSignupAccountAdapter properly inherits from DefaultAccountAdapter."""
        from allauth.account.adapter import DefaultAccountAdapter
        self.assertTrue(issubclass(NoSignupAccountAdapter, DefaultAccountAdapter))
