from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from django.test import TransactionTestCase, override_settings
from django.urls import reverse

from accounts.adapters import NoSignupAccountAdapter
from tests.factories import UserFactory

User = get_user_model()


class AccountsIntegrationTest(TransactionTestCase):
    """
    Integration tests that verify the accounts app works correctly with Django's auth system.
    """

    def test_full_authentication_flow(self):
        """Test the complete authentication flow."""
        # Create a user
        user = UserFactory.create_user()

        # Verify user can authenticate
        authenticated = authenticate(username=user.username, password="testpass123")
        self.assertIsNotNone(authenticated)
        self.assertEqual(authenticated.id, user.id)

        # Verify wrong password fails
        not_authenticated = authenticate(username=user.username, password="wrongpass")
        self.assertIsNone(not_authenticated)

        # Verify user can login
        login_success = self.client.login(username=user.username, password="testpass123")
        self.assertTrue(login_success)

        # Verify user is logged in
        response = self.client.get("/")
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        # Logout
        self.client.logout()

        # Verify user is logged out
        response = self.client.get("/")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=False)
    def test_registration_disabled_integration(self):
        """Test that registration is properly disabled across the system."""
        # Try to access signup URL
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("account_login"))

        # Try to POST to signup
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

        # Verify user was not created
        self.assertFalse(User.objects.filter(username="blockeduser").exists())

        # Verify adapter reports signup is closed
        adapter = NoSignupAccountAdapter()
        request = self.client.get("/").wsgi_request
        self.assertFalse(adapter.is_open_for_signup(request))

    def test_user_permissions_integration(self):
        """Test user permissions work correctly with CustomUser."""
        # Create regular user
        user = UserFactory.create_user()

        # Create staff user
        staff_user = UserFactory.create_staff_user()

        # Create superuser
        superuser = UserFactory.create_superuser()

        # Test regular user cannot access admin
        self.client.login(username=user.username, password="testpass123")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)  # Redirects to login
        self.client.logout()

        # Test staff user can access admin login but may have limited permissions
        self.client.login(username=staff_user.username, password="testpass123")
        response = self.client.get("/admin/")
        self.assertIn(response.status_code, [200, 302])  # Depends on permissions
        self.client.logout()

        # Test superuser has full admin access
        self.client.login(username=superuser.username, password="testpass123")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)

        # Superuser can access user admin
        response = self.client.get(reverse("admin:accounts_customuser_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_user_model_constraints(self):
        """Test database constraints on the CustomUser model."""
        # Create first user
        user = UserFactory.create_user()

        # Try to create duplicate username - should fail
        with self.assertRaises(IntegrityError):
            UserFactory.create_user(username=user.username)

    def test_password_hashing(self):
        """Test that passwords are properly hashed."""
        user = UserFactory.create_user(password="plaintext123")

        # Password should not be stored as plaintext
        self.assertNotEqual(user.password, "plaintext123")

        # Password should be hashed (Django's hash format - could be MD5 in tests)
        self.assertTrue(user.password.startswith(("pbkdf2_sha256$", "md5$")))

        # Should be able to verify password
        self.assertTrue(user.check_password("plaintext123"))
        self.assertFalse(user.check_password("wrongpassword"))

    def test_session_management(self):
        """Test session management with CustomUser."""
        user = UserFactory.create_user()

        # Login creates a session
        self.client.login(username=user.username, password="testpass123")
        self.assertIn("_auth_user_id", self.client.session)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

        # Logout clears the session
        self.client.logout()
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_user_update_workflow(self):
        """Test updating user information."""
        user = UserFactory.create_user()
        original_password = "testpass123"

        # Update email
        user.email = "newemail@example.com"
        user.save()

        # Verify change persisted
        updated_user = User.objects.get(id=user.id)
        self.assertEqual(updated_user.email, "newemail@example.com")

        # Update password
        user.set_password("newpassword123")
        user.save()

        # Verify old password doesn't work
        self.assertFalse(user.check_password(original_password))
        # Verify new password works
        self.assertTrue(user.check_password("newpassword123"))

    @override_settings(ACCOUNT_ALLOW_REGISTRATION=True)
    def test_registration_enabled_integration(self):
        """Test behavior when registration is explicitly enabled."""
        adapter = NoSignupAccountAdapter()
        request = self.client.get("/").wsgi_request

        # Adapter should report signup is open
        self.assertTrue(adapter.is_open_for_signup(request))

        # Note: The view still redirects because we've overridden it,
        # but the adapter reports correctly
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 302)  # Our custom view always redirects

    def test_user_manager_methods(self):
        """Test that CustomUser uses Django's UserManager correctly."""
        # Test create_user
        user = UserFactory.create_user()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

        # Test create_superuser
        superuser = UserFactory.create_superuser()
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_active)

        # Test get_by_natural_key (used for authentication)
        found_user = User.objects.get_by_natural_key(user.username)
        self.assertEqual(found_user.id, user.id)
