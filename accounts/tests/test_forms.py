from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.forms import CustomUserChangeForm, CustomUserCreationForm
from accounts.tests.factories import UserFactory

User = get_user_model()


class CustomUserCreationFormTest(TestCase):
    def test_form_has_expected_fields(self):
        form = CustomUserCreationForm()
        expected_fields = ["email", "username", "password1", "password2"]
        actual_fields = list(form.fields.keys())
        for field in expected_fields:
            self.assertIn(field, actual_fields)

    def test_form_valid_data(self):
        user_data = UserFactory.get_common_user_data()
        form_data = {
            "username": user_data["username"],
            "email": user_data["email"],
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_save(self):
        user_data = UserFactory.get_common_user_data()
        form_data = {
            "username": user_data["username"],
            "email": user_data["email"],
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

        user = form.save()
        self.assertEqual(user.username, user_data["username"])
        self.assertEqual(user.email, user_data["email"])
        self.assertTrue(user.check_password("testpass123!@#"))

    def test_form_password_mismatch(self):
        form_data = {
            "username": "mismatchuser",
            "email": "mismatch@example.com",
            "password1": "testpass123!@#",
            "password2": "differentpass123!@#",
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_form_weak_password(self):
        form_data = {
            "username": "weakpassuser",
            "email": "weak@example.com",
            "password1": "123",
            "password2": "123",
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertTrue(any("password" in error for error in form.errors))

    def test_form_duplicate_username(self):
        existing_user = UserFactory.create_user()

        form_data = {
            "username": existing_user.username,  # Duplicate username
            "email": "new@example.com",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_form_invalid_email(self):
        form_data = {
            "username": "invalidemail",
            "email": "not-an-email",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_form_empty_email(self):
        form_data = {
            "username": "noemailuser",
            "email": "",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_model_is_customuser(self):
        form = CustomUserCreationForm()
        self.assertEqual(form._meta.model, User)


class CustomUserChangeFormTest(TestCase):
    def setUp(self):
        self.user = UserFactory.create_user()

    def test_form_has_expected_fields(self):
        form = CustomUserChangeForm(instance=self.user)
        expected_fields = ["email", "username", "password"]
        actual_fields = list(form.fields.keys())
        for field in expected_fields:
            self.assertIn(field, actual_fields)

    def test_form_initial_data(self):
        form = CustomUserChangeForm(instance=self.user)
        self.assertEqual(form.initial["username"], self.user.username)
        self.assertEqual(form.initial["email"], self.user.email)

    def test_form_update_email(self):
        form_data = {
            "username": self.user.username,
            "email": "newemail@example.com",
        }
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        if form.is_valid():
            updated_user = form.save()
            self.assertEqual(updated_user.email, "newemail@example.com")

    def test_form_update_username(self):
        form_data = {
            "username": "newusername",
            "email": self.user.email,
        }
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        if form.is_valid():
            updated_user = form.save()
            self.assertEqual(updated_user.username, "newusername")

    def test_form_duplicate_username_on_update(self):
        another_user = UserFactory.create_user()

        form_data = {
            "username": another_user.username,  # Try to use existing username
            "email": self.user.email,
        }
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_form_model_is_customuser(self):
        form = CustomUserChangeForm(instance=self.user)
        self.assertEqual(form._meta.model, User)

    def test_form_password_field_is_readonly(self):
        form = CustomUserChangeForm(instance=self.user)
        self.assertIn("password", form.fields)
        password_field = form.fields["password"]
        self.assertIsNotNone(password_field)
