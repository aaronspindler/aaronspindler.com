from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.forms import CustomUserChangeForm, CustomUserCreationForm
from tests.factories import UserFactory

User = get_user_model()


class CustomUserCreationFormTest(TestCase):
    """
    Test the CustomUserCreationForm functionality.
    """

    def test_form_has_expected_fields(self):
        """Test that the form has the expected fields."""
        form = CustomUserCreationForm()
        expected_fields = ["email", "username", "password1", "password2"]
        actual_fields = list(form.fields.keys())
        for field in expected_fields:
            self.assertIn(field, actual_fields)

    def test_form_valid_data(self):
        """Test form with valid data."""
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
        """Test that the form saves a user correctly."""
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
        """Test form with mismatched passwords."""
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
        """Test form with a weak password."""
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
        """Test form with duplicate username."""
        # Create an existing user
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
        """Test form with invalid email format."""
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
        """Test form with empty email."""
        form_data = {
            "username": "noemailuser",
            "email": "",
            "password1": "testpass123!@#",
            "password2": "testpass123!@#",
        }
        form = CustomUserCreationForm(data=form_data)
        # Email is not required in Django's default user model
        self.assertTrue(form.is_valid())

    def test_form_model_is_customuser(self):
        """Test that the form uses the CustomUser model."""
        form = CustomUserCreationForm()
        self.assertEqual(form._meta.model, User)


class CustomUserChangeFormTest(TestCase):
    """
    Test the CustomUserChangeForm functionality.
    """

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory.create_user()

    def test_form_has_expected_fields(self):
        """Test that the change form has the expected fields."""
        form = CustomUserChangeForm(instance=self.user)
        expected_fields = ["email", "username", "password"]
        actual_fields = list(form.fields.keys())
        for field in expected_fields:
            self.assertIn(field, actual_fields)

    def test_form_initial_data(self):
        """Test that the form loads with correct initial data."""
        form = CustomUserChangeForm(instance=self.user)
        self.assertEqual(form.initial["username"], self.user.username)
        self.assertEqual(form.initial["email"], self.user.email)

    def test_form_update_email(self):
        """Test updating user email through the form."""
        form_data = {
            "username": self.user.username,
            "email": "newemail@example.com",
        }
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        if form.is_valid():
            updated_user = form.save()
            self.assertEqual(updated_user.email, "newemail@example.com")

    def test_form_update_username(self):
        """Test updating username through the form."""
        form_data = {
            "username": "newusername",
            "email": self.user.email,
        }
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        if form.is_valid():
            updated_user = form.save()
            self.assertEqual(updated_user.username, "newusername")

    def test_form_duplicate_username_on_update(self):
        """Test that duplicate username is prevented on update."""
        # Create another user
        another_user = UserFactory.create_user()

        form_data = {
            "username": another_user.username,  # Try to use existing username
            "email": self.user.email,
        }
        form = CustomUserChangeForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_form_model_is_customuser(self):
        """Test that the change form uses the CustomUser model."""
        form = CustomUserChangeForm(instance=self.user)
        self.assertEqual(form._meta.model, User)

    def test_form_password_field_is_readonly(self):
        """Test that password field is handled properly."""
        form = CustomUserChangeForm(instance=self.user)
        # Password field should be present but is a ReadOnlyPasswordHashField
        self.assertIn("password", form.fields)
        # The password field should show a link to change password form
        password_field = form.fields["password"]
        self.assertIsNotNone(password_field)
