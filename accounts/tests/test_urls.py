from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse

from accounts.views import signup_disabled
from blog.tests.factories import MockDataFactory


class AccountsURLTest(SimpleTestCase):
    def test_signup_url_resolves(self):
        url = reverse("account_signup")
        self.assertEqual(url, "/accounts/signup/")
        resolver = resolve(url)
        self.assertEqual(resolver.func, signup_disabled)

    def test_signup_url_name(self):
        url = reverse("account_signup")
        self.assertEqual(url, "/accounts/signup/")

    def test_signup_disabled_view_mapping(self):
        resolver = resolve("/accounts/signup/")
        self.assertEqual(resolver.func, signup_disabled)
        self.assertEqual(resolver.url_name, "account_signup")

    def test_login_url_exists(self):
        url = reverse("account_login")
        self.assertIsNotNone(url)
        self.assertIn("/login/", url)

    def test_signup_redirect_target(self):
        login_url = reverse("account_login")
        self.assertIsNotNone(login_url)

    def test_url_patterns_include_accounts(self):
        response = self.client.get("/accounts/signup/")
        self.assertEqual(response.status_code, 302)


class AccountsIntegrationTest(TestCase):
    def test_signup_flow_disabled(self):
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("account_login"))

    def test_login_page_accessible(self):
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)

    def test_logout_url_exists(self):
        url = reverse("account_logout")
        self.assertIsNotNone(url)

    def test_password_reset_url_exists(self):
        url = reverse("account_reset_password")
        self.assertIsNotNone(url)

    def test_direct_signup_path_disabled(self):
        response = self.client.get("/accounts/signup/")
        self.assertEqual(response.status_code, 302)

        response = self.client.get("/accounts/signup/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "login")

    def test_post_to_signup_disabled(self):
        form_data = MockDataFactory.get_common_form_data()["user_form"]
        response = self.client.post(reverse("account_signup"), form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("account_login"))

        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.assertFalse(User.objects.filter(username=form_data["username"]).exists())
