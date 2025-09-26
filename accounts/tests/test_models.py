from django.test import TestCase
from django.contrib.auth import get_user_model
from tests.factories import UserFactory

User = get_user_model()


class CustomUserModelTest(TestCase):
    """
    Test the CustomUser model functionality.
    """

    def setUp(self):
        """Set up test data."""
        self.user_data = UserFactory.get_common_user_data()
        self.user = UserFactory.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password=self.user_data['password']
        )

    def test_create_user(self):
        """Test creating a user with email and username."""
        self.assertTrue(isinstance(self.user, User))
        self.assertEqual(self.user.username, self.user_data['username'])
        self.assertEqual(self.user.email, self.user_data['email'])
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_create_superuser(self):
        """Test creating a superuser."""
        superuser = UserFactory.create_superuser()
        self.assertTrue(isinstance(superuser, User))
        self.assertTrue(superuser.is_active)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_user_str_method(self):
        """Test the string representation of the user model."""
        self.assertEqual(str(self.user), self.user_data['email'])

    def test_user_with_empty_email(self):
        """Test creating a user with an empty email."""
        user = UserFactory.create_user(username='noemail', email='')
        self.assertEqual(str(user), '')
        self.assertEqual(user.username, 'noemail')

    def test_user_full_name(self):
        """Test user's full name methods."""
        self.user.first_name = 'Test'
        self.user.last_name = 'User'
        self.user.save()
        
        self.assertEqual(self.user.get_full_name(), 'Test User')
        self.assertEqual(self.user.get_short_name(), 'Test')

    def test_duplicate_username(self):
        """Test that duplicate usernames are not allowed."""
        with self.assertRaises(Exception):
            UserFactory.create_user(
                username=self.user_data['username'],  # Same as existing user
                email='different@example.com'
            )

    def test_user_permissions(self):
        """Test user permission methods."""
        self.assertFalse(self.user.has_perm('some_app.some_permission'))
        self.assertFalse(self.user.has_module_perms('some_app'))
        
        # Superuser should have all permissions
        superuser = UserFactory.create_superuser()
        self.assertTrue(superuser.has_perm('some_app.some_permission'))
        self.assertTrue(superuser.has_module_perms('some_app'))
