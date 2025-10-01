import uuid
from unittest import mock
from accounts.models import CustomUser
from config.testcases import BaseTestCase
from django.test import RequestFactory
from django.urls import reverse

from utils.common_list_choices import get_interval_choices, get_region_choices
from utils.models import NotificationEmail, NotificationPhoneNumber
from utils.phone_numbers import clean_phone_number
from utils.security import (
    get_client_ip,
    get_request_headers,
    generate_fingerprint,
    get_request_fingerprint_data,
    parse_user_agent,
    is_suspicious_request,
)

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


class SecurityUtilsTests(BaseTestCase):
    """Tests for request fingerprinting and IP tracking utilities."""
    
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
    
    def test_get_client_ip_from_remote_addr(self):
        """Test IP extraction from REMOTE_ADDR."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        self.assertEqual(get_client_ip(request), '192.168.1.1')
    
    def test_get_client_ip_from_x_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 192.168.1.1'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        self.assertEqual(get_client_ip(request), '10.0.0.1')
    
    def test_get_client_ip_from_x_real_ip(self):
        """Test IP extraction from X-Real-IP header."""
        request = self.factory.get('/')
        request.META['HTTP_X_REAL_IP'] = '172.16.0.1'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        self.assertEqual(get_client_ip(request), '172.16.0.1')
    
    def test_get_client_ip_priority(self):
        """Test that X-Forwarded-For takes priority over X-Real-IP."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1'
        request.META['HTTP_X_REAL_IP'] = '172.16.0.1'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        self.assertEqual(get_client_ip(request), '10.0.0.1')
    
    def test_get_client_ip_unknown(self):
        """Test IP extraction returns 'unknown' when no IP available."""
        request = self.factory.get('/')
        self.assertEqual(get_client_ip(request), 'unknown')
    
    def test_get_request_headers(self):
        """Test extraction of relevant request headers."""
        request = self.factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        request.META['HTTP_ACCEPT'] = 'text/html'
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'en-US'
        
        headers = get_request_headers(request)
        
        self.assertEqual(headers['HTTP_USER_AGENT'], 'Mozilla/5.0')
        self.assertEqual(headers['HTTP_ACCEPT'], 'text/html')
        self.assertEqual(headers['HTTP_ACCEPT_LANGUAGE'], 'en-US')
    
    def test_get_request_headers_empty(self):
        """Test header extraction with no headers present."""
        request = self.factory.get('/')
        headers = get_request_headers(request)
        self.assertEqual(headers, {})
    
    def test_generate_fingerprint_with_ip(self):
        """Test fingerprint generation including IP address."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        
        fingerprint = generate_fingerprint(request, include_ip=True)
        
        self.assertIsInstance(fingerprint, str)
        self.assertEqual(len(fingerprint), 64)
    
    def test_generate_fingerprint_without_ip(self):
        """Test fingerprint generation excluding IP address."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        
        fingerprint_with_ip = generate_fingerprint(request, include_ip=True)
        fingerprint_without_ip = generate_fingerprint(request, include_ip=False)
        
        self.assertNotEqual(fingerprint_with_ip, fingerprint_without_ip)
    
    def test_generate_fingerprint_consistency(self):
        """Test that same request produces same fingerprint."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        request.META['HTTP_ACCEPT'] = 'text/html'
        
        fingerprint1 = generate_fingerprint(request)
        fingerprint2 = generate_fingerprint(request)
        
        self.assertEqual(fingerprint1, fingerprint2)
    
    def test_generate_fingerprint_different_requests(self):
        """Test that different requests produce different fingerprints."""
        request1 = self.factory.get('/')
        request1.META['REMOTE_ADDR'] = '192.168.1.1'
        request1.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        
        request2 = self.factory.get('/')
        request2.META['REMOTE_ADDR'] = '192.168.1.2'
        request2.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        
        fingerprint1 = generate_fingerprint(request1)
        fingerprint2 = generate_fingerprint(request2)
        
        self.assertNotEqual(fingerprint1, fingerprint2)
    
    def test_get_request_fingerprint_data(self):
        """Test comprehensive fingerprint data extraction."""
        request = self.factory.get('/test-path/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        request.META['HTTP_ACCEPT'] = 'text/html'
        
        data = get_request_fingerprint_data(request)
        
        self.assertEqual(data['ip_address'], '192.168.1.1')
        self.assertEqual(data['user_agent'], 'Mozilla/5.0')
        self.assertEqual(data['method'], 'GET')
        self.assertEqual(data['path'], '/test-path/')
        self.assertFalse(data['is_secure'])
        self.assertFalse(data['is_ajax'])
        self.assertIn('fingerprint', data)
        self.assertIn('fingerprint_no_ip', data)
        self.assertIsInstance(data['headers'], dict)
    
    def test_get_request_fingerprint_data_ajax(self):
        """Test fingerprint data correctly identifies AJAX requests."""
        request = self.factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        data = get_request_fingerprint_data(request)
        
        self.assertTrue(data['is_ajax'])
    
    def test_parse_user_agent_chrome(self):
        """Test user agent parsing for Chrome."""
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        result = parse_user_agent(ua)
        
        self.assertEqual(result['browser'], 'Chrome')
        self.assertEqual(result['os'], 'Windows')
        self.assertEqual(result['device'], 'Desktop')
    
    def test_parse_user_agent_firefox(self):
        """Test user agent parsing for Firefox."""
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        result = parse_user_agent(ua)
        
        self.assertEqual(result['browser'], 'Firefox')
        self.assertEqual(result['os'], 'Windows')
    
    def test_parse_user_agent_safari(self):
        """Test user agent parsing for Safari."""
        ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        result = parse_user_agent(ua)
        
        self.assertEqual(result['browser'], 'Safari')
        self.assertEqual(result['os'], 'macOS')
    
    def test_parse_user_agent_mobile(self):
        """Test user agent parsing for mobile devices."""
        ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        result = parse_user_agent(ua)
        
        self.assertEqual(result['os'], 'iOS')
        self.assertEqual(result['device'], 'Mobile')
    
    def test_parse_user_agent_edge(self):
        """Test user agent parsing for Edge."""
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
        result = parse_user_agent(ua)
        
        self.assertEqual(result['browser'], 'Edge')
        self.assertEqual(result['os'], 'Windows')
    
    def test_parse_user_agent_unknown(self):
        """Test user agent parsing with unknown UA."""
        result = parse_user_agent('unknown')
        
        self.assertIsNone(result['browser'])
        self.assertIsNone(result['os'])
        self.assertIsNone(result['device'])
    
    def test_parse_user_agent_empty(self):
        """Test user agent parsing with empty string."""
        result = parse_user_agent('')
        
        self.assertIsNone(result['browser'])
        self.assertIsNone(result['os'])
    
    def test_is_suspicious_request_normal(self):
        """Test that normal requests are not flagged as suspicious."""
        request = self.factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'
        request.META['HTTP_ACCEPT'] = 'text/html'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        is_suspicious, reason = is_suspicious_request(request)
        
        self.assertFalse(is_suspicious)
        self.assertIsNone(reason)
    
    def test_is_suspicious_request_no_user_agent(self):
        """Test that requests without User-Agent are flagged."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        is_suspicious, reason = is_suspicious_request(request)
        
        self.assertTrue(is_suspicious)
        self.assertEqual(reason, 'Missing User-Agent header')
    
    def test_is_suspicious_request_bot_user_agent(self):
        """Test that bot user agents are flagged."""
        request = self.factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'python-requests/2.25.1'
        request.META['HTTP_ACCEPT'] = 'text/html'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        is_suspicious, reason = is_suspicious_request(request)
        
        self.assertTrue(is_suspicious)
        self.assertIn('Suspicious User-Agent pattern', reason)
    
    def test_is_suspicious_request_curl(self):
        """Test that curl requests are flagged."""
        request = self.factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'curl/7.68.0'
        request.META['HTTP_ACCEPT'] = '*/*'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        is_suspicious, reason = is_suspicious_request(request)
        
        self.assertTrue(is_suspicious)
        self.assertIn('curl', reason)
    
    def test_is_suspicious_request_no_accept_header(self):
        """Test that requests without Accept header are flagged."""
        request = self.factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        is_suspicious, reason = is_suspicious_request(request)
        
        self.assertTrue(is_suspicious)
        self.assertEqual(reason, 'Missing Accept header')
    
    def test_is_suspicious_request_googlebot_allowed(self):
        """Test that legitimate search engine bots are not flagged."""
        request = self.factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
        request.META['HTTP_ACCEPT'] = 'text/html'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        is_suspicious, reason = is_suspicious_request(request)
        
        self.assertFalse(is_suspicious)
        self.assertIsNone(reason)


class RequestFingerprintModelTests(BaseTestCase):
    """Test RequestFingerprint model."""
    
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
    
    def test_create_from_request_basic(self):
        """Test creating a RequestFingerprint from a basic request."""
        from utils.models import RequestFingerprint
        
        request = self.factory.get('/test-page/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        request.META['HTTP_ACCEPT'] = 'text/html,application/xhtml+xml'
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'en-US,en;q=0.9'
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.user = self.user
        
        fingerprint = RequestFingerprint.create_from_request(request)
        
        self.assertIsNotNone(fingerprint.id)
        self.assertEqual(fingerprint.ip_address, '192.168.1.100')
        self.assertEqual(fingerprint.method, 'GET')
        self.assertEqual(fingerprint.path, '/test-page/')
        self.assertEqual(fingerprint.user, self.user)
        self.assertFalse(fingerprint.is_secure)
        self.assertFalse(fingerprint.is_ajax)
        self.assertEqual(len(fingerprint.fingerprint), 64)  # SHA256 length
        self.assertEqual(len(fingerprint.fingerprint_no_ip), 64)
        self.assertNotEqual(fingerprint.fingerprint, fingerprint.fingerprint_no_ip)
    
    def test_create_from_request_with_user_agent_parsing(self):
        """Test that user agent is properly parsed."""
        from utils.models import RequestFingerprint
        
        request = self.factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        request.META['HTTP_ACCEPT'] = 'text/html'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = mock.MagicMock(is_authenticated=False)
        
        fingerprint = RequestFingerprint.create_from_request(request)
        
        self.assertIn('Chrome', fingerprint.browser)
        self.assertIn('Windows', fingerprint.os)
    
    def test_create_from_request_suspicious(self):
        """Test that suspicious requests are flagged."""
        from utils.models import RequestFingerprint
        
        request = self.factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'curl/7.68.0'
        request.META['HTTP_ACCEPT'] = '*/*'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = mock.MagicMock(is_authenticated=False)
        
        fingerprint = RequestFingerprint.create_from_request(request)
        
        self.assertTrue(fingerprint.is_suspicious)
        self.assertIn('curl', fingerprint.suspicious_reason)
    
    def test_create_from_request_ajax(self):
        """Test AJAX request detection."""
        from utils.models import RequestFingerprint
        
        request = self.factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        request.META['HTTP_ACCEPT'] = 'application/json'
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = mock.MagicMock(is_authenticated=False)
        
        fingerprint = RequestFingerprint.create_from_request(request)
        
        self.assertTrue(fingerprint.is_ajax)
    
    def test_create_from_request_headers_stored(self):
        """Test that headers are properly stored as JSON."""
        from utils.models import RequestFingerprint
        
        request = self.factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        request.META['HTTP_ACCEPT'] = 'text/html'
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'en-US'
        request.META['HTTP_ACCEPT_ENCODING'] = 'gzip, deflate'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = mock.MagicMock(is_authenticated=False)
        
        fingerprint = RequestFingerprint.create_from_request(request)
        
        self.assertIsInstance(fingerprint.headers, dict)
        self.assertIn('HTTP_USER_AGENT', fingerprint.headers)
        self.assertIn('HTTP_ACCEPT', fingerprint.headers)
        self.assertIn('HTTP_ACCEPT_LANGUAGE', fingerprint.headers)
    
    def test_request_fingerprint_str(self):
        """Test string representation of RequestFingerprint."""
        from utils.models import RequestFingerprint
        
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        request.META['HTTP_ACCEPT'] = 'text/html'
        request.META['REMOTE_ADDR'] = '10.0.0.1'
        request.user = mock.MagicMock(is_authenticated=False)
        
        fingerprint = RequestFingerprint.create_from_request(request)
        
        str_repr = str(fingerprint)
        self.assertIn('10.0.0.1', str_repr)
        self.assertIn('GET', str_repr)
        self.assertIn('/test/', str_repr)
    
    def test_fingerprint_ordering(self):
        """Test that fingerprints are ordered by creation date (newest first)."""
        from utils.models import RequestFingerprint
        
        request = self.factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        request.META['HTTP_ACCEPT'] = 'text/html'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = mock.MagicMock(is_authenticated=False)
        
        fp1 = RequestFingerprint.create_from_request(request)
        fp2 = RequestFingerprint.create_from_request(request)
        fp3 = RequestFingerprint.create_from_request(request)
        
        all_fps = list(RequestFingerprint.objects.all())
        self.assertEqual(all_fps[0].id, fp3.id)
        self.assertEqual(all_fps[1].id, fp2.id)
        self.assertEqual(all_fps[2].id, fp1.id)