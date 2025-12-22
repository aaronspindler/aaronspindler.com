from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from django.test import TransactionTestCase, override_settings
from django.urls import reverse

from accounts.adapters import NoSignupAccountAdapter
from accounts.tests.factories import UserFactory

User = get_user_model()


class AccountsIntegrationTest(TransactionTestCase):
    def test_full_authentication_flow(self):
        user = UserFactory.create_user()

        authenticated = authenticate(username=user.username, password="testpass123")
        self.assertIsNotNone(authenticated)
        self.assertEqual(authenticated.id, user.id)

        not_authenticated = authenticate(username=user.username, password="wrongpass")
        self.assertIsNone(not_authenticated)

        login_success = self.client.login(username=user.username, password="testpass123")
        self.assertTrue(login_success)

        response = self.client.get("/")
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        self.client.logout()

        response = self.client.get("/")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=False)
    def test_registration_disabled_integration(self):
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("account_login"))

        response = self.client.post(
            reverse("account_signup"),
            {
                "username": "blockeduser",
                "email": "blocked@example.com",
                "password1": "testpass123",
                "password2": "testpass123",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.assertFalse(User.objects.filter(username="blockeduser").exists())

        adapter = NoSignupAccountAdapter()
        request = self.client.get("/").wsgi_request
        self.assertFalse(adapter.is_open_for_signup(request))

    def test_user_permissions_integration(self):
        user = UserFactory.create_user()

        staff_user = UserFactory.create_staff_user()

        superuser = UserFactory.create_superuser()

        self.client.login(username=user.username, password="testpass123")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)  # Redirects to login
        self.client.logout()

        self.client.login(username=staff_user.username, password="testpass123")
        response = self.client.get("/admin/")
        self.assertIn(response.status_code, [200, 302])  # Depends on permissions
        self.client.logout()

        self.client.login(username=superuser.username, password="testpass123")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("admin:accounts_customuser_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_user_model_constraints(self):
        user = UserFactory.create_user()

        with self.assertRaises(IntegrityError):
            UserFactory.create_user(username=user.username)

    def test_password_hashing(self):
        user = UserFactory.create_user(password="plaintext123")

        self.assertNotEqual(user.password, "plaintext123")

        # Password should be hashed (Django's hash format - could be MD5 in tests)
        self.assertTrue(user.password.startswith(("pbkdf2_sha256$", "md5$")))

        self.assertTrue(user.check_password("plaintext123"))
        self.assertFalse(user.check_password("wrongpassword"))

    def test_session_management(self):
        user = UserFactory.create_user()

        self.client.login(username=user.username, password="testpass123")
        self.assertIn("_auth_user_id", self.client.session)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

        self.client.logout()
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_user_update_workflow(self):
        user = UserFactory.create_user()
        original_password = "testpass123"

        user.email = "newemail@example.com"
        user.save()

        updated_user = User.objects.get(id=user.id)
        self.assertEqual(updated_user.email, "newemail@example.com")

        user.set_password("newpassword123")
        user.save()

        self.assertFalse(user.check_password(original_password))
        self.assertTrue(user.check_password("newpassword123"))

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=True)
    def test_registration_enabled_integration(self):
        adapter = NoSignupAccountAdapter()
        request = self.client.get("/").wsgi_request

        self.assertTrue(adapter.is_open_for_signup(request))

        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 302)  # Our custom view always redirects

    def test_user_manager_methods(self):
        user = UserFactory.create_user()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

        superuser = UserFactory.create_superuser()
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_active)

        found_user = User.objects.get_by_natural_key(user.username)
        self.assertEqual(found_user.id, user.id)
