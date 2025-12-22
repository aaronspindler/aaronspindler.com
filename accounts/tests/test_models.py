from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.tests.factories import UserFactory

User = get_user_model()


class CustomUserModelTest(TestCase):
    def setUp(self):
        self.user_data = UserFactory.get_common_user_data()
        self.user = UserFactory.create_user(
            username=self.user_data["username"],
            email=self.user_data["email"],
            password=self.user_data["password"],
        )

    def test_create_user(self):
        self.assertTrue(isinstance(self.user, User))
        self.assertEqual(self.user.username, self.user_data["username"])
        self.assertEqual(self.user.email, self.user_data["email"])
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_create_superuser(self):
        superuser = UserFactory.create_superuser()
        self.assertTrue(isinstance(superuser, User))
        self.assertTrue(superuser.is_active)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_user_str_method(self):
        self.assertEqual(str(self.user), self.user_data["email"])

    def test_user_with_empty_email(self):
        user = UserFactory.create_user(username="noemail", email="")
        self.assertEqual(str(user), "")
        self.assertEqual(user.username, "noemail")

    def test_user_full_name(self):
        self.user.first_name = "Test"
        self.user.last_name = "User"
        self.user.save()

        self.assertEqual(self.user.get_full_name(), "Test User")
        self.assertEqual(self.user.get_short_name(), "Test")

    def test_duplicate_username(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            UserFactory.create_user(
                username=self.user_data["username"],  # Same as existing user
                email="different@example.com",
            )

    def test_user_permissions(self):
        self.assertFalse(self.user.has_perm("some_app.some_permission"))
        self.assertFalse(self.user.has_module_perms("some_app"))

        superuser = UserFactory.create_superuser()
        self.assertTrue(superuser.has_perm("some_app.some_permission"))
        self.assertTrue(superuser.has_module_perms("some_app"))
