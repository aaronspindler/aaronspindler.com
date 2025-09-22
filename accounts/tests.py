from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages


class SignupDisabledTestCase(TestCase):
    """Test that signup functionality is properly disabled"""
    
    def test_signup_url_redirects_to_login(self):
        """Test that accessing signup URL redirects to login page"""
        response = self.client.get(reverse('account_signup'), follow=True)
        
        # Check that we're redirected to the login page
        self.assertRedirects(response, reverse('account_login'))
        
        # Check that the info message is displayed
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("Registration is currently disabled", str(messages[0]))
    
    def test_signup_post_redirects_to_login(self):
        """Test that POST to signup URL also redirects to login"""
        response = self.client.post(reverse('account_signup'), {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123'
        }, follow=True)
        
        # Check that we're redirected to the login page
        self.assertRedirects(response, reverse('account_login'))
        
        # Verify no user was created
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.assertEqual(User.objects.filter(email='test@example.com').count(), 0)
