from django.test import TestCase, Client
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.admin import CustomUserAdmin
from accounts.forms import CustomUserCreationForm, CustomUserChangeForm

User = get_user_model()


class CustomUserAdminTest(TestCase):
    """
    Test the CustomUserAdmin configuration.
    """

    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = CustomUserAdmin(User, self.site)
        
        # Create a superuser for admin access
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Create a regular user to manage
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
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
        self.assertEqual(self.admin.list_display, ['email', 'username'])

    def test_admin_model_is_customuser(self):
        """Test that admin is configured for CustomUser model."""
        self.assertEqual(self.admin.model, User)

    def test_admin_login_required(self):
        """Test that admin requires login."""
        url = reverse('admin:accounts_customuser_changelist')
        response = self.client.get(url)
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/admin/login/' in response.url)

    def test_admin_superuser_access(self):
        """Test that superuser can access user admin."""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('admin:accounts_customuser_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_admin_list_users(self):
        """Test that admin can list users."""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('admin:accounts_customuser_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that both users are listed
        self.assertContains(response, 'admin@example.com')
        self.assertContains(response, 'test@example.com')

    def test_admin_add_user(self):
        """Test that admin can access the add user page."""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('admin:accounts_customuser_add')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that the form is present
        self.assertContains(response, 'username')
        self.assertContains(response, 'email')
        self.assertContains(response, 'password1')
        self.assertContains(response, 'password2')

    def test_admin_change_user(self):
        """Test that admin can access the change user page."""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('admin:accounts_customuser_change', args=[self.user.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that user data is displayed
        self.assertContains(response, 'testuser')
        self.assertContains(response, 'test@example.com')

    def test_admin_delete_user(self):
        """Test that admin can access the delete user page."""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('admin:accounts_customuser_delete', args=[self.user.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that delete confirmation is shown
        self.assertContains(response, 'Are you sure')
        self.assertContains(response, 'testuser')

    def test_admin_search_users(self):
        """Test searching users in admin."""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('admin:accounts_customuser_changelist')
        
        # Search by username
        response = self.client.get(url, {'q': 'testuser'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')
        self.assertNotContains(response, 'admin@example.com')
        
        # Search by email
        response = self.client.get(url, {'q': 'admin@'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin@example.com')
        self.assertNotContains(response, 'test@example.com')

    def test_admin_regular_user_no_access(self):
        """Test that regular users cannot access admin."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('admin:accounts_customuser_changelist')
        response = self.client.get(url)
        
        # Should redirect to admin login
        self.assertEqual(response.status_code, 302)

    def test_admin_create_user_post(self):
        """Test creating a user through admin interface."""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('admin:accounts_customuser_add')
        
        post_data = {
            'username': 'newadminuser',
            'email': 'newadmin@example.com',
            'password1': 'newpass123!@#',
            'password2': 'newpass123!@#',
        }
        
        response = self.client.post(url, post_data)
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Verify user was created
        new_user = User.objects.get(username='newadminuser')
        self.assertEqual(new_user.email, 'newadmin@example.com')
        self.assertTrue(new_user.check_password('newpass123!@#'))

    def test_admin_update_user_post(self):
        """Test updating a user through admin interface."""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('admin:accounts_customuser_change', args=[self.user.id])
        
        # Get the form to get all required fields
        response = self.client.get(url)
        form = response.context['adminform'].form
        
        # Update email
        post_data = form.initial.copy()
        post_data['email'] = 'updated@example.com'
        post_data['username'] = 'testuser'  # Keep username
        
        response = self.client.post(url, post_data)
        
        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)
        
        # Verify user was updated
        updated_user = User.objects.get(id=self.user.id)
        self.assertEqual(updated_user.email, 'updated@example.com')

    def test_admin_inheritance(self):
        """Test that CustomUserAdmin inherits from UserAdmin."""
        from django.contrib.auth.admin import UserAdmin
        self.assertTrue(issubclass(CustomUserAdmin, UserAdmin))
