from django.db import IntegrityError
from django.urls import reverse
from actions.models import Action, ActionStatus
from actions.tasks import check_action_status_badge
import uuid
from unittest import mock
from config.testcases import BaseTestCase
from utils.models import NotificationEmail, NotificationPhoneNumber

class ActionTaskTests(BaseTestCase):
    def test_check_action_status_badge(self):
        check_action_status_badge(self.success_action.id)
        self.assertEqual(ActionStatus.objects.get(action=self.success_action, checker='badge').status, 'success')
        
    def test_check_action_status_badge_failure(self):
        check_action_status_badge(self.failure_action.id)
        self.assertEqual(ActionStatus.objects.get(action=self.failure_action, checker='badge').status, 'failure')


class ActionModelTests(BaseTestCase):
    def test_action_creation(self):
        action = Action.objects.create(owner=self.paid_user, url="https://github.com/FredFlintstone/Speeder/actions/workflows/test-and-deploy.yml")
        self.assertEqual(action.owner, self.paid_user)
        self.assertEqual(action.url, "https://github.com/FredFlintstone/Speeder/actions/workflows/test-and-deploy.yml")
    
    def test_action_creation_duplicate(self):
        Action.objects.create(owner=self.paid_user, url="https://github.com/FredFlintstone/Speeder/actions/workflows/test-and-deploy.yml")
        with self.assertRaises(IntegrityError):
            Action.objects.create(owner=self.paid_user, url="https://github.com/FredFlintstone/Speeder/actions/workflows/test-and-deploy.yml")
            
    def test_action_parse_url(self):
        action = Action.objects.create(owner=self.paid_user, url="https://github.com/FredFlintstone/Speeder/actions/workflows/test-and-deploy.yml")
        self.assertEqual(action.repo_name, "FredFlintstone/Speeder")
        self.assertEqual(action.action_name, "test-and-deploy.yml")

class ActionViewTests(BaseTestCase):
    def test_add_action_view_private(self):
        self.client.force_login(self.paid_user)
        pre_count = Action.objects.filter(is_private=True).count()
        mock_return = {'private_actions': True}
        with mock.patch('accounts.models.CustomUser.get_subscription_metadata', return_value=mock_return):
            response = self.client.post(reverse("add_action"), {"url": "https://github.com/FredFlintstone/Speeder/actions/workflows/test-and-deploy.yml", "is_private": "on"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.filter(is_private=True).count(), pre_count + 1)
        
    def test_add_action_view_public(self):
        self.client.force_login(self.paid_user)
        pre_count = Action.objects.filter(is_private=False).count()
        mock_return = {'private_actions': False}
        with mock.patch('accounts.models.CustomUser.get_subscription_metadata', return_value=mock_return):
            response = self.client.post(reverse("add_action"), {"url": "https://github.com/FredFlintstone/Speeder/actions/workflows/test-and-deploy.yml", "is_private": "off"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.filter(is_private=False).count(), pre_count + 1)
        
    def test_add_action_view_private_no_subscription(self):
        self.client.force_login(self.paid_user)
        pre_count = Action.objects.filter(is_private=True).count()
        mock_return = {'private_actions': False}
        with mock.patch('accounts.models.CustomUser.get_subscription_metadata', return_value=mock_return):
            response = self.client.post(reverse("add_action"), {"url": "https://github.com/FredFlintstone/Speeder/actions/workflows/test-and-deploy.yml"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.filter(is_private=True).count(), pre_count)
        
    def test_add_action_view_duplicate(self):
        Action.objects.create(owner=self.paid_user, url="https://github.com/FredFlintstone/Speeder/actions/workflows/test-and-deploy.yml")
        self.client.force_login(self.paid_user)
        pre_count = Action.objects.count()
        response = self.client.post(reverse("add_action"), {"url": "https://github.com/FredFlintstone/Speeder/actions/workflows/test-and-deploy.yml"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), pre_count)
        self.assertContains(response, "Action already exists!")
        
    def test_add_action_view_invalid_url(self):
        self.client.force_login(self.paid_user)
        pre_count = Action.objects.count()
        response = self.client.post(reverse("add_action"), {"url": "https://asdf.com/FredFlintstone/Speeder/actions/workflows/test-and-deploy.yml"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), pre_count)
        self.assertContains(response, "Please enter a valid GitHub Actions workflow URL.")
        
    def test_add_action_view_invalid_url2(self):
        self.client.force_login(self.paid_user)
        pre_count = Action.objects.count()
        response = self.client.post(reverse("add_action"), {"url": "https://github.com/FredFlintstone/Speeder/test-and-deploy.yml"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), pre_count)
        self.assertContains(response, "Please enter a valid GitHub Actions workflow URL.")
        
    def test_actions_status_view(self):
        ActionStatus.objects.create(action=self.success_action, status='success')
        self.client.force_login(self.paid_user)
        response = self.client.get(reverse("action_status", kwargs={"private_id": self.success_action.private_id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"success")
    
    def test_action_status_view_failure(self):
        self.client.force_login(self.paid_user)
        response = self.client.get(reverse("action_status", kwargs={"private_id": self.failure_action.private_id}))
        self.assertEqual(response.status_code, 404)
        
    def test_action_status_view_not_found(self):
        self.client.force_login(self.paid_user)
        response = self.client.get(reverse("action_status", kwargs={"private_id": uuid.uuid4()}))
        self.assertEqual(response.status_code, 404)
        
    def test_action_status_view_logged_out(self):
        self.client.logout()
        ActionStatus.objects.create(action=self.success_action, status='success')
        response = self.client.get(reverse("action_status", kwargs={"private_id": self.success_action.private_id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"success")
        
    def test_delete_action_view(self):
        self.client.force_login(self.paid_user)
        pre_count = Action.objects.count()
        response = self.client.post(reverse("delete_action", kwargs={"pk": self.success_action.id}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), pre_count - 1)
    
    def test_delete_action_view_not_found(self):
        self.client.force_login(self.paid_user)
        pre_count = Action.objects.count()
        response = self.client.post(reverse("delete_action", kwargs={"pk": 999999}), follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Action.objects.count(), pre_count)
        
    def test_delete_action_view_logged_out(self):
        self.client.logout()
        pre_count = Action.objects.count()
        response = self.client.post(reverse("delete_action", kwargs={"pk": self.success_action.id}), follow=True)
        self.assertEqual(Action.objects.count(), pre_count)
    
    def test_delete_action_view_not_owner(self):
        self.client.force_login(self.other_user)
        pre_count = Action.objects.count()
        response = self.client.post(reverse("delete_action", kwargs={"pk": self.success_action.id}), follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Action.objects.count(), pre_count)
        
    def test_action_available_notification_methods(self):
        self.client.force_login(self.paid_user)
        
        # Create notification methods for the user
        email = NotificationEmail.objects.create(user=self.paid_user, email='test@example.com', verified=True)
        phone = NotificationPhoneNumber.objects.create(user=self.paid_user, phone_number='+1234567890', verified=True)
        
        # Add these methods to the action
        self.success_action.notify_emails.add(email)
        self.success_action.notify_phone_numbers.add(phone)
        
        response = self.client.get(reverse("action_available_notification_methods", kwargs={"pk": self.success_action.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('emails', data)
        self.assertIn('phone_numbers', data)
        self.assertEqual(len(data['emails']), 1)
        self.assertEqual(len(data['phone_numbers']), 1)
        self.assertEqual(data['emails'][0]['email'], 'test@example.com')
        self.assertEqual(data['phone_numbers'][0]['phone_number'], '+1234567890')

    def test_action_available_notification_methods_no_methods(self):
        self.client.force_login(self.paid_user)
        
        response = self.client.get(reverse("action_available_notification_methods", kwargs={"pk": self.success_action.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('emails', data)
        self.assertIn('phone_numbers', data)
        self.assertEqual(len(data['emails']), 0)
        self.assertEqual(len(data['phone_numbers']), 0)

    def test_action_available_notification_methods_not_owner(self):
        self.client.force_login(self.other_user)
        
        response = self.client.get(reverse("action_available_notification_methods", kwargs={"pk": self.success_action.id}))
        self.assertEqual(response.status_code, 404)

    def test_action_available_notification_methods_logged_out(self):
        self.client.logout()
        response = self.client.get(reverse("action_available_notification_methods", kwargs={"pk": self.success_action.id}))
        self.assertEqual(response.status_code, 302)

    def test_action_available_notification_methods_not_found(self):
        self.client.force_login(self.paid_user)
        
        response = self.client.get(reverse("action_available_notification_methods", kwargs={"pk": 999999}))
        self.assertEqual(response.status_code, 404)