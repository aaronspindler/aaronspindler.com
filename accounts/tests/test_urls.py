from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse

from accounts.views import signup_disabled
from blog.tests.factories import MockDataFactory


class AccountsURLTest(SimpleTestCase):
    """
    Test URL configuration for the accounts app.
    """

    def test_signup_url_resolves(self):
        """Test that the signup URL resolves to the correct view."""
        url = reverse("account_signup")
        self.assertEqual(url, "/accounts/signup/")
        resolver = resolve(url)
        self.assertEqual(resolver.func, signup_disabled)

    def test_signup_url_name(self):
        """Test that the signup URL name works correctly."""
        url = reverse("account_signup")
        self.assertEqual(url, "/accounts/signup/")

    def test_signup_disabled_view_mapping(self):
        """Test that /accounts/signup/ maps to signup_disabled view."""
        resolver = resolve("/accounts/signup/")
        self.assertEqual(resolver.func, signup_disabled)
        self.assertEqual(resolver.url_name, "account_signup")

    def test_login_url_exists(self):
        """Test that the login URL exists (from allauth)."""
        # This URL comes from allauth, but we should ensure it's available
        url = reverse("account_login")
        self.assertIsNotNone(url)
        # Typically this would be /accounts/login/
        self.assertIn("/login/", url)

    def test_signup_redirect_target(self):
        """Test that the signup redirect target (login) is available."""
        # The signup_disabled view redirects to account_login
        login_url = reverse("account_login")
        self.assertIsNotNone(login_url)

    def test_url_patterns_include_accounts(self):
        """Test that accounts URLs are included in the project."""
        # Test that our custom signup URL overrides the default
        response = self.client.get("/accounts/signup/")
        # Should redirect (302) to login, not show a signup form (200)
        self.assertEqual(response.status_code, 302)


class AccountsIntegrationTest(TestCase):
    """
    Integration tests for accounts URLs with the full Django setup.
    """

    def test_signup_flow_disabled(self):
        """Test that the entire signup flow is properly disabled."""
        # Try to access signup
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("account_login"))

    def test_login_page_accessible(self):
        """Test that the login page is still accessible."""
        response = self.client.get(reverse("account_login"))
        # Should return 200 (page loads) not 302 (redirect)
        self.assertEqual(response.status_code, 200)

    def test_logout_url_exists(self):
        """Test that logout URL exists (from allauth)."""
        # This comes from allauth
        url = reverse("account_logout")
        self.assertIsNotNone(url)

    def test_password_reset_url_exists(self):
        """Test that password reset URL exists (from allauth)."""
        # This comes from allauth
        url = reverse("account_reset_password")
        self.assertIsNotNone(url)

    def test_direct_signup_path_disabled(self):
        """Test accessing signup directly by path is disabled."""
        response = self.client.get("/accounts/signup/")
        self.assertEqual(response.status_code, 302)

        # Follow redirect
        response = self.client.get("/accounts/signup/", follow=True)
        self.assertEqual(response.status_code, 200)
        # Should end up at login page
        self.assertContains(response, "login")

    def test_post_to_signup_disabled(self):
        """Test that POST to signup is also disabled."""
        form_data = MockDataFactory.get_common_form_data()["user_form"]
        response = self.client.post(reverse("account_signup"), form_data)
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("account_login"))

        # Verify user was NOT created
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.assertFalse(User.objects.filter(username=form_data["username"]).exists())
