from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from accounts.adapters import NoSignupAccountAdapter


class NoSignupAccountAdapterTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.adapter = NoSignupAccountAdapter()

    def test_signup_disabled_by_default(self):
        request = self.factory.get("/accounts/signup/")
        is_open = self.adapter.is_open_for_signup(request)
        self.assertFalse(is_open)

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=False)
    def test_signup_explicitly_disabled(self):
        request = self.factory.get("/accounts/signup/")
        is_open = self.adapter.is_open_for_signup(request)
        self.assertFalse(is_open)

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=True)
    def test_signup_explicitly_enabled(self):
        request = self.factory.get("/accounts/signup/")
        is_open = self.adapter.is_open_for_signup(request)
        self.assertTrue(is_open)

    def test_signup_redirect_url(self):
        request = self.factory.get("/accounts/signup/")
        redirect_url = self.adapter.get_signup_redirect_url(request)
        expected_url = reverse("account_login")
        self.assertEqual(redirect_url, expected_url)

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=False)
    def test_adapter_prevents_registration_flow(self):
        request = self.factory.post(
            "/accounts/signup/",
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "testpass123",
                "password2": "testpass123",
            },
        )

        self.assertFalse(self.adapter.is_open_for_signup(request))

        redirect_url = self.adapter.get_signup_redirect_url(request)
        self.assertEqual(redirect_url, reverse("account_login"))

    def test_adapter_inheritance(self):
        from allauth.account.adapter import DefaultAccountAdapter

        self.assertTrue(issubclass(NoSignupAccountAdapter, DefaultAccountAdapter))
