import uuid
from unittest import mock
from accounts.models import CustomUser
from config.testcases import BaseTestCase
from django.urls import reverse

from utils.common_list_choices import get_interval_choices, get_region_choices
from utils.models import NotificationEmail, NotificationPhoneNumber
from utils.phone_numbers import clean_phone_number

class UtilUtilsTests(BaseTestCase):
    def test_phone_number_clean(self):
        self.assertEqual(clean_phone_number('123-456-7890'), '1234567890')
        self.assertEqual(clean_phone_number('1234567890'), '1234567890')
        self.assertEqual(clean_phone_number('1234567890123456'), '1234567890123456')
        self.assertEqual(clean_phone_number('12345678901234567890'), '12345678901234567890')

class UtilsCommonListChoicesTests(BaseTestCase):
    def test_get_interval_choices(self):
        self.assertEqual(get_interval_choices('5M'), [('5M', '5 Minutes')])
        self.assertEqual(get_interval_choices('3M'), [('5M', '5 Minutes'), ('3M', '3 Minutes')])
        self.assertEqual(get_interval_choices('1M'), [('5M', '5 Minutes'), ('3M', '3 Minutes'), ('1M', '1 Minute')])
        self.assertEqual(get_interval_choices('30S'), [('5M', '5 Minutes'), ('3M', '3 Minutes'), ('1M', '1 Minute'), ('30S', '30 Seconds')])
    
    def test_get_region_choices(self):
        self.assertEqual(get_region_choices(['CA']), [(11, 'Canada (Central)'), (24, 'Canada (Calgary)')])
        self.assertEqual(len(get_region_choices(['US'])), 4)
        self.assertEqual(len(get_region_choices(['US', 'CA'])), 6)
        self.assertEqual(len(get_region_choices(['US', 'CA', 'EU'])), 14)
        self.assertEqual(len(get_region_choices([])), 1)
        self.assertEqual(len(get_region_choices(["CA", "US", "EU", "AP", "AF", "SA", "ME"])), 28)


class UtilsViewTests(BaseTestCase):
    def test_add_phone_success(self):
        self.client.force_login(self.paid_user)
        mock_return = {'sms_notifications': True}
        with mock.patch('accounts.models.CustomUser.get_subscription_metadata', return_value=mock_return):
            response = self.client.post(reverse('add_phone'), {'phone_number': '123-456-7890'}, follow=True)
        self.assertTrue(self.paid_user.notificationphonenumber_set.filter(phone_number='1234567890').exists())
        self.assertContains(response, 'Phone number added successfully')

    def test_add_phone_unauthenticated(self):
        pre_count = NotificationPhoneNumber.objects.count()
        response = self.client.post(reverse('add_phone'), {'phone_number': '123-456-7890'})
        self.assertEqual(NotificationPhoneNumber.objects.count(), pre_count)

    def test_add_phone_no_number(self):
        self.client.force_login(self.paid_user)
        mock_return = {'sms_notifications': True}
        with mock.patch('accounts.models.CustomUser.get_subscription_metadata', return_value=mock_return):
            response = self.client.post(reverse('add_phone'), {}, follow=True)
        self.assertContains(response, 'Phone number is required')
        
    def test_add_phone_sms_notifications_false(self):
        self.client.force_login(self.paid_user)
        mock_return = {'sms_notifications': False}
        with mock.patch('accounts.models.CustomUser.get_subscription_metadata', return_value=mock_return):
            response = self.client.post(reverse('add_phone'), {}, follow=True)
        self.assertContains(response, 'SMS notifications are not available on your current plan.')

    def test_add_phone_method_not_allowed(self):
        self.client.force_login(self.paid_user)
        mock_return = {'sms_notifications': True}
        with mock.patch('accounts.models.CustomUser.get_subscription_metadata', return_value=mock_return):
            response = self.client.get(reverse('add_phone'))
        self.assertEqual(response.status_code, 405)
        
    def test_add_phone_duplicate(self):
        self.client.force_login(self.paid_user)
        NotificationPhoneNumber.objects.create(user=self.paid_user, phone_number='1234567890')
        mock_return = {'sms_notifications': True}
        with mock.patch('accounts.models.CustomUser.get_subscription_metadata', return_value=mock_return):
            response = self.client.post(reverse('add_phone'), {'phone_number': '1234567890'}, follow=True)
        self.assertContains(response, 'Phone number already exists')
        self.assertEqual(self.paid_user.notificationphonenumber_set.filter(phone_number='1234567890').count(), 1)
        
    def test_add_email_success(self):
        self.client.force_login(self.paid_user)
        response = self.client.post(reverse('add_email'), {'email': 'test@example.com'}, follow=True)
        self.assertTrue(self.paid_user.notificationemail_set.filter(email='test@example.com').exists())
        self.assertContains(response, 'Email added successfully')

    def test_add_email_unauthenticated(self):
        pre_count = NotificationEmail.objects.count()
        response = self.client.post(reverse('add_email'), {'email': 'test@example.com'})
        self.assertEqual(NotificationEmail.objects.count(), pre_count)
        self.assertEqual(response.status_code, 302)  # Redirect to login page

    def test_add_email_no_email(self):
        self.client.force_login(self.paid_user)
        response = self.client.post(reverse('add_email'), {}, follow=True)
        self.assertContains(response, 'Email is required')
    
    def test_add_email_duplicate(self):
        self.client.force_login(self.paid_user)
        NotificationEmail.objects.create(user=self.paid_user, email='existing@example.com')
        response = self.client.post(reverse('add_email'), {'email': 'existing@example.com'}, follow=True)
        self.assertContains(response, 'Email already exists')
        self.assertEqual(self.paid_user.notificationemail_set.filter(email='existing@example.com').count(), 1)

    def test_add_email_method_not_allowed(self):
        self.client.force_login(self.paid_user)
        response = self.client.get(reverse('add_email'))
        self.assertEqual(response.status_code, 405)
        
    def test_delete_phone_success(self):
        self.client.force_login(self.paid_user)
        phone_number = NotificationPhoneNumber.objects.create(user=self.paid_user, phone_number='1234567890')
        response = self.client.post(reverse('delete_phone', args=[phone_number.id]), follow=True)
        self.assertFalse(NotificationPhoneNumber.objects.filter(id=phone_number.id).exists())
        self.assertContains(response, 'Phone number deleted successfully')
        
    def test_delete_phone_nonexistent(self):
        self.client.force_login(self.paid_user)
        non_existent_id = 9999
        response = self.client.post(reverse('delete_phone', args=[non_existent_id]), follow=True)
        self.assertEqual(response.status_code, 404)

    def test_delete_phone_wrong_user(self):
        other_user = CustomUser.objects.create_user(username='otheruser', password='testpass')
        phone_number = NotificationPhoneNumber.objects.create(user=other_user, phone_number='1234567890')
        self.client.force_login(self.paid_user)
        response = self.client.post(reverse('delete_phone', args=[phone_number.id]), follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(NotificationPhoneNumber.objects.filter(id=phone_number.id).exists())

    def test_delete_phone_unauthenticated(self):
        phone_number = NotificationPhoneNumber.objects.create(user=self.paid_user, phone_number='1234567890')
        response = self.client.post(reverse('delete_phone', args=[phone_number.id]))
        self.assertEqual(response.status_code, 302)  # Redirect to login page
        self.assertTrue(NotificationPhoneNumber.objects.filter(id=phone_number.id).exists())

    def test_delete_phone_method_not_allowed(self):
        self.client.force_login(self.paid_user)
        phone_number = NotificationPhoneNumber.objects.create(user=self.paid_user, phone_number='1234567890')
        response = self.client.get(reverse('delete_phone', args=[phone_number.id]))
        self.assertEqual(response.status_code, 405)
        
    def test_delete_email_success(self):
        self.client.force_login(self.paid_user)
        email = NotificationEmail.objects.create(user=self.paid_user, email='test@example.com')
        response = self.client.post(reverse('delete_email', args=[email.id]), follow=True)
        self.assertFalse(NotificationEmail.objects.filter(id=email.id).exists())
        self.assertContains(response, 'Email deleted successfully')

    def test_delete_email_unauthenticated(self):
        email = NotificationEmail.objects.create(user=self.paid_user, email='test@example.com')
        response = self.client.post(reverse('delete_email', args=[email.id]))
        self.assertEqual(response.status_code, 302)  # Redirect to login page
        self.assertTrue(NotificationEmail.objects.filter(id=email.id).exists())

    def test_delete_email_method_not_allowed(self):
        self.client.force_login(self.paid_user)
        email = NotificationEmail.objects.create(user=self.paid_user, email='test@example.com')
        response = self.client.get(reverse('delete_email', args=[email.id]))
        self.assertEqual(response.status_code, 405)

    def test_delete_email_nonexistent(self):
        self.client.force_login(self.paid_user)
        non_existent_id = 9999
        response = self.client.post(reverse('delete_email', args=[non_existent_id]), follow=True)
        self.assertEqual(response.status_code, 404)

    def test_delete_email_wrong_user(self):
        other_user = CustomUser.objects.create_user(username='otheruser', password='testpass')
        email = NotificationEmail.objects.create(user=other_user, email='other@example.com')
        self.client.force_login(self.paid_user)
        response = self.client.post(reverse('delete_email', args=[email.id]), follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(NotificationEmail.objects.filter(id=email.id).exists())
        
    def test_verify_phone_success(self):
        self.client.force_login(self.paid_user)
        phone_number = NotificationPhoneNumber.objects.create(user=self.paid_user, phone_number='1234567890')
        response = self.client.post(reverse('verify_phone', args=[phone_number.id]), {'code': phone_number.verification_code}, follow=True)
        self.assertTrue(NotificationPhoneNumber.objects.filter(id=phone_number.id, verified=True).exists())
        self.assertContains(response, 'Phone number verified successfully')

    def test_verify_phone_invalid_code(self):
        self.client.force_login(self.paid_user)
        phone_number = NotificationPhoneNumber.objects.create(user=self.paid_user, phone_number='1234567890')
        response = self.client.post(reverse('verify_phone', args=[phone_number.id]), {'code': '1234'}, follow=True)
        self.assertFalse(NotificationPhoneNumber.objects.filter(id=phone_number.id, verified=True).exists())
        self.assertContains(response, 'Invalid verification code')

    def test_verify_phone_unauthenticated(self):
        self.client.logout()
        phone_number = NotificationPhoneNumber.objects.create(user=self.paid_user, phone_number='1234567890')
        response = self.client.post(reverse('verify_phone', args=[phone_number.id]))
        self.assertEqual(response.status_code, 302)  # Redirect to login page
        self.assertFalse(NotificationPhoneNumber.objects.filter(id=phone_number.id, verified=True).exists())

    def test_verify_phone_method_not_allowed(self):
        self.client.force_login(self.paid_user)
        phone_number = NotificationPhoneNumber.objects.create(user=self.paid_user, phone_number='1234567890')
        response = self.client.get(reverse('verify_phone', args=[phone_number.id]))
        self.assertEqual(response.status_code, 405)
        
    def test_verify_email_success_link(self):
        self.client.force_login(self.paid_user)
        email = NotificationEmail.objects.create(user=self.paid_user, email='test@example.com')
        response = self.client.get(reverse('verify_email', args=[email.id, email.verification_code]), follow=True)
        self.assertTrue(NotificationEmail.objects.filter(id=email.id, verified=True).exists())
        self.assertContains(response, 'Email verified successfully')

    def test_verify_email_success_post(self):
        self.client.force_login(self.paid_user)
        email = NotificationEmail.objects.create(user=self.paid_user, email='test@example.com')
        response = self.client.post(reverse('verify_email', args=[email.id]), {'code': email.verification_code_small}, follow=True)
        self.assertTrue(NotificationEmail.objects.filter(id=email.id, verified=True).exists())
        self.assertContains(response, 'Email verified successfully')
        
    def test_verify_email_invalid_code(self):
        self.client.force_login(self.paid_user)
        email = NotificationEmail.objects.create(user=self.paid_user, email='test@example.com')
        response = self.client.post(reverse('verify_email', args=[email.id]), {'code': '1234'}, follow=True)
        self.assertFalse(NotificationEmail.objects.filter(id=email.id, verified=True).exists())
        self.assertContains(response, 'Invalid verification code')
        
    def test_verify_email_invalid_link(self):
        self.client.force_login(self.paid_user)
        email = NotificationEmail.objects.create(user=self.paid_user, email='test@example.com')
        response = self.client.get(reverse('verify_email', args=[email.id, '1234']), follow=True)
        self.assertFalse(NotificationEmail.objects.filter(id=email.id, verified=True).exists())
        self.assertContains(response, 'Invalid verification code')
        
    def test_verify_email_unauthenticated(self):
        # This needs to pass because the email hot link could be clicked in a different browser or device
        self.client.logout()
        email = NotificationEmail.objects.create(user=self.paid_user, email='test@example.com')
        response = self.client.get(reverse('verify_email', args=[email.id, email.verification_code]), follow=True)
        self.assertTrue(NotificationEmail.objects.filter(id=email.id, verified=True).exists())
        self.assertContains(response, 'Email verified successfully')
        
    def test_unsubscribe_success(self):
        self.client.force_login(self.paid_user)
        email = NotificationEmail.objects.create(user=self.paid_user, email='test@example.com')
        pre_count = NotificationEmail.objects.count()
        response = self.client.get(reverse('unsubscribe', args=[email.unsubscribe_code]), follow=True)
        self.assertEqual(NotificationEmail.objects.count(), pre_count - 1)
        self.assertFalse(NotificationEmail.objects.filter(id=email.id).exists())
        self.assertContains(response, 'been unsubscribed from all notifications')
        
    def test_unsubscribe_invalid_code(self):
        self.client.force_login(self.paid_user)
        email = NotificationEmail.objects.create(user=self.paid_user, email='test@example.com')
        pre_count = NotificationEmail.objects.count()
        response = self.client.get(reverse('unsubscribe', args=[uuid.uuid4()]), follow=True)
        self.assertEqual(NotificationEmail.objects.count(), pre_count)
        self.assertEqual(response.status_code, 404)
        
    def test_unsubscribe_unauthenticated(self):
        self.client.logout()
        email = NotificationEmail.objects.create(user=self.paid_user, email='test@example.com')
        pre_count = NotificationEmail.objects.count()
        response = self.client.get(reverse('unsubscribe', args=[email.unsubscribe_code]), follow=True)
        self.assertEqual(NotificationEmail.objects.count(), pre_count - 1)
        self.assertFalse(NotificationEmail.objects.filter(id=email.id).exists())
        self.assertContains(response, 'been unsubscribed from all notifications')