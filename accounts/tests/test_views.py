from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from accounts.views import signup_disabled
from tests.factories import MockDataFactory


class SignupDisabledViewTest(TestCase):
    """
    Test the signup_disabled view functionality.
    """

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()

    def test_signup_disabled_redirects_to_login(self):
        """Test that the signup_disabled view redirects to login page."""
        response = self.client.get("/accounts/signup/")
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("/login/"))

    def test_signup_disabled_shows_message(self):
        """Test that the signup_disabled view shows an informative message."""
        response = self.client.get("/accounts/signup/", follow=True)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        message = str(messages[0])
        self.assertIn("Registration is currently disabled", message)
        self.assertIn("contact an administrator", message)

    def test_signup_disabled_direct_function_call(self):
        """Test the signup_disabled function directly."""
        request = self.factory.get("/accounts/signup/")

        # Add message storage to request
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        response = signup_disabled(request)

        # Check redirect
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("/login/"))

        # Check message was added
        stored_messages = list(messages)
        self.assertEqual(len(stored_messages), 1)
        self.assertIn("Registration is currently disabled", str(stored_messages[0]))

    def test_post_to_signup_disabled(self):
        """Test POST request to signup_disabled view."""
        form_data = MockDataFactory.get_common_form_data()["user_form"]
        response = self.client.post("/accounts/signup/", form_data)

        # Should still redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("/login/"))

    def test_signup_disabled_preserves_next_parameter(self):
        """Test that next parameter is preserved during redirect."""
        # Note: The current implementation doesn't preserve the next parameter,
        # but this test documents the current behavior
        response = self.client.get("/accounts/signup/?next=/dashboard/")
        self.assertEqual(response.status_code, 302)
        # Current implementation just redirects to login without preserving next
        self.assertTrue(response.url.endswith("/login/"))

    def test_message_level(self):
        """Test that the message uses the correct level (info)."""
        response = self.client.get("/accounts/signup/", follow=True)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        message = messages[0]
        # Django message levels: DEBUG=10, INFO=20, SUCCESS=25, WARNING=30, ERROR=40
        self.assertEqual(message.level, 20)  # INFO level

    def test_multiple_requests_dont_accumulate_messages(self):
        """Test that messages don't accumulate across multiple requests."""
        # First request
        response1 = self.client.get("/accounts/signup/", follow=True)
        messages1 = list(response1.context["messages"])
        self.assertEqual(len(messages1), 1)

        # Second request - should also have only one message
        response2 = self.client.get("/accounts/signup/", follow=True)
        messages2 = list(response2.context["messages"])
        self.assertEqual(len(messages2), 1)
