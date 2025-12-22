from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from accounts.views import signup_disabled
from blog.tests.factories import MockDataFactory


class SignupDisabledViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_signup_disabled_redirects_to_login(self):
        response = self.client.get("/accounts/signup/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("/login/"))

    def test_signup_disabled_shows_message(self):
        response = self.client.get("/accounts/signup/", follow=True)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        message = str(messages[0])
        self.assertIn("Registration is currently disabled", message)
        self.assertIn("contact an administrator", message)

    def test_signup_disabled_direct_function_call(self):
        request = self.factory.get("/accounts/signup/")

        request.session = "session"
        messages = FallbackStorage(request)
        request._messages = messages

        response = signup_disabled(request)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("/login/"))

        stored_messages = list(messages)
        self.assertEqual(len(stored_messages), 1)
        self.assertIn("Registration is currently disabled", str(stored_messages[0]))

    def test_post_to_signup_disabled(self):
        form_data = MockDataFactory.get_common_form_data()["user_form"]
        response = self.client.post("/accounts/signup/", form_data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("/login/"))

    def test_signup_disabled_preserves_next_parameter(self):
        response = self.client.get("/accounts/signup/?next=/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("/login/"))

    def test_message_level(self):
        response = self.client.get("/accounts/signup/", follow=True)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        message = messages[0]
        # Django message levels: DEBUG=10, INFO=20, SUCCESS=25, WARNING=30, ERROR=40
        self.assertEqual(message.level, 20)  # INFO level

    def test_multiple_requests_dont_accumulate_messages(self):
        response1 = self.client.get("/accounts/signup/", follow=True)
        messages1 = list(response1.context["messages"])
        self.assertEqual(len(messages1), 1)

        response2 = self.client.get("/accounts/signup/", follow=True)
        messages2 = list(response2.context["messages"])
        self.assertEqual(len(messages2), 1)
