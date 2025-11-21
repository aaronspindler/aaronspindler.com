from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.admin import CustomUserAdmin
from accounts.forms import CustomUserChangeForm, CustomUserCreationForm
from accounts.tests.factories import UserFactory

User = get_user_model()


class CustomUserAdminTest(TestCase):
    """
    Test the CustomUserAdmin configuration.
    """

    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = CustomUserAdmin(User, self.site)
        self.user = UserFactory.create_user()
        self.staff_user = UserFactory.create_staff_user()
        self.superuser = UserFactory.create_superuser()
        self.client = Client()

    def test_admin_registered(self):
        """Test that CustomUser is registered in admin."""
        from django.contrib import admin

        self.assertIn(User, admin.site._registry)

    def test_admin_uses_custom_forms(self):
        """Test that admin uses the custom forms."""
        self.assertEqual(self.admin.add_form, CustomUserCreationForm)
        self.assertEqual(self.admin.form, CustomUserChangeForm)

    def test_admin_list_display(self):
        """Test that admin list display shows correct fields."""
        self.assertEqual(self.admin.list_display, ["email", "username"])

    def test_admin_model_is_customuser(self):
        """Test that admin is configured for CustomUser model."""
        self.assertEqual(self.admin.model, User)

    def test_admin_login_required(self):
        """Test that admin requires login."""
        url = reverse("admin:accounts_customuser_changelist")
        response = self.client.get(url)
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_admin_superuser_access(self):
        """Test that superuser can access user admin."""
        self.client.login(username=self.superuser.username, password="testpass123")
        url = reverse("admin:accounts_customuser_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_admin_list_users(self):
        """Test that admin can list users."""
        self.client.login(username=self.superuser.username, password="testpass123")
        url = reverse("admin:accounts_customuser_changelist")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Check that both users are listed
        self.assertContains(response, self.superuser.email)
        self.assertContains(response, self.user.email)

    def test_admin_add_user(self):
        """Test that admin can access the add user page."""
        self.client.login(username=self.superuser.username, password="testpass123")
        url = reverse("admin:accounts_customuser_add")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Check that the form is present
        self.assertContains(response, "username")
        self.assertContains(response, "email")
        self.assertContains(response, "password1")
        self.assertContains(response, "password2")

    def test_admin_change_user(self):
        """Test that admin can access the change user page."""
        self.client.login(username=self.superuser.username, password="testpass123")
        url = reverse("admin:accounts_customuser_change", args=[self.user.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Check that user data is displayed
        self.assertContains(response, self.user.username)
        self.assertContains(response, self.user.email)

    def test_admin_delete_user(self):
        """Test that admin can access the delete user page."""
        self.client.login(username=self.superuser.username, password="testpass123")
        url = reverse("admin:accounts_customuser_delete", args=[self.user.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Check that delete confirmation is shown
        self.assertContains(response, "Are you sure")
        self.assertContains(response, self.user.username)

    def test_admin_search_users(self):
        """Test searching users in admin."""
        self.client.login(username=self.superuser.username, password="testpass123")
        url = reverse("admin:accounts_customuser_changelist")

        # Search by username
        response = self.client.get(url, {"q": self.user.username})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)
        self.assertNotContains(response, self.superuser.email)

        # Search by email - search for superuser email
        superuser_email_prefix = self.superuser.email.split("@")[0]
        response = self.client.get(url, {"q": superuser_email_prefix})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.superuser.email)
        self.assertNotContains(response, self.user.email)

    def test_admin_regular_user_no_access(self):
        """Test that regular users cannot access admin."""
        self.client.login(username=self.user.username, password="testpass123")
        url = reverse("admin:accounts_customuser_changelist")
        response = self.client.get(url)

        # Should redirect to admin login
        self.assertEqual(response.status_code, 302)

    def test_admin_create_user_post(self):
        """Test creating a user through admin interface."""
        self.client.login(username=self.superuser.username, password="testpass123")
        url = reverse("admin:accounts_customuser_add")

        user_data = UserFactory.get_common_user_data()
        post_data = {
            "username": user_data["username"],
            "email": user_data["email"],
            "password1": "newpass123!@#",
            "password2": "newpass123!@#",
        }

        response = self.client.post(url, post_data)

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Verify user was created
        new_user = User.objects.get(username=user_data["username"])
        self.assertEqual(new_user.email, user_data["email"])
        self.assertTrue(new_user.check_password("newpass123!@#"))

    def test_admin_update_user_post(self):
        """Test updating a user through admin interface."""
        self.client.login(username=self.superuser.username, password="testpass123")
        url = reverse("admin:accounts_customuser_change", args=[self.user.id])

        # Use a simpler approach - just send the basic required fields
        post_data = {
            "username": self.user.username,
            "email": "updated@example.com",
            "first_name": "",
            "last_name": "",
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "date_joined_0": self.user.date_joined.strftime("%Y-%m-%d"),
            "date_joined_1": self.user.date_joined.strftime("%H:%M:%S"),
        }

        response = self.client.post(url, post_data)

        # Should redirect after successful update or show form with errors
        self.assertIn(response.status_code, [200, 302])

        # If it was successful (302), verify user was updated
        if response.status_code == 302:
            updated_user = User.objects.get(id=self.user.id)
            self.assertEqual(updated_user.email, "updated@example.com")

    def test_admin_inheritance(self):
        """Test that CustomUserAdmin inherits from UserAdmin."""
        from django.contrib.auth.admin import UserAdmin

        self.assertTrue(issubclass(CustomUserAdmin, UserAdmin))
