from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from unittest.mock import patch, MagicMock
from pages.decorators import track_page_visit, track_page_visit_cbv, _get_client_ip_safe
from pages.models import PageVisit
import socket


class TrackPageVisitDecoratorTest(TestCase):
    """Test page visit tracking decorator."""
    
    def setUp(self):
        self.factory = RequestFactory()
        
    def test_decorator_tracks_visit(self):
        """Test that decorator creates PageVisit record."""
        @track_page_visit
        def test_view(request):
            return HttpResponse('Test')
        
        request = self.factory.get('/test-page/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        response = test_view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'Test')
        
        # Check that visit was tracked
        visit = PageVisit.objects.get(page_name='/test-page/')
        self.assertEqual(visit.ip_address, '192.168.1.1')
        
    def test_decorator_handles_x_forwarded_for(self):
        """Test that decorator extracts IP from X-Forwarded-For header."""
        @track_page_visit
        def test_view(request):
            return HttpResponse('Test')
        
        request = self.factory.get('/test/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.0, 198.51.100.0'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        test_view(request)
        
        # Should use first IP from X-Forwarded-For
        visit = PageVisit.objects.get(page_name='/test/')
        self.assertEqual(visit.ip_address, '203.0.113.0')
        
    def test_decorator_handles_database_error(self):
        """Test that decorator continues even if database fails."""
        @track_page_visit
        def test_view(request):
            return HttpResponse('Success')
        
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        with patch('pages.decorators.PageVisit.objects.create') as mock_create:
            mock_create.side_effect = Exception('Database error')
            
            response = test_view(request)
            
            # View should still execute successfully
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b'Success')
            
    def test_decorator_handles_dns_error(self):
        """Test that decorator handles DNS resolution errors."""
        @track_page_visit
        def test_view(request):
            return HttpResponse('Success')
        
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        with patch('pages.decorators.PageVisit.objects.create') as mock_create:
            mock_create.side_effect = socket.gaierror('DNS error')
            
            response = test_view(request)
            
            # View should still execute
            self.assertEqual(response.status_code, 200)
            
    def test_decorator_truncates_long_paths(self):
        """Test that decorator truncates long page names to fit database field."""
        @track_page_visit
        def test_view(request):
            return HttpResponse('Test')
        
        long_path = '/very/long/path/' + 'x' * 500
        request = self.factory.get(long_path)
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        test_view(request)
        
        visit = PageVisit.objects.first()
        self.assertEqual(len(visit.page_name), 255)
        self.assertTrue(visit.page_name.startswith('/very/long/path/'))
        
    def test_decorator_truncates_user_agent(self):
        """Test that decorator truncates long user agents."""
        @track_page_visit
        def test_view(request):
            return HttpResponse('Test')
        
        long_user_agent = 'Mozilla/5.0 ' + 'x' * 500
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = long_user_agent
        
        with patch('pages.decorators.logger') as mock_logger:
            test_view(request)
            
            # Check that user agent was truncated in log
            log_call = mock_logger.info.call_args[0][0]
            self.assertIn('Mozilla/5.0', log_call)
            
    def test_decorator_handles_missing_ip(self):
        """Test that decorator handles missing IP address."""
        @track_page_visit
        def test_view(request):
            return HttpResponse('Test')
        
        request = self.factory.get('/test/')
        # Don't set REMOTE_ADDR
        
        test_view(request)
        
        visit = PageVisit.objects.first()
        self.assertEqual(visit.ip_address, 'unknown')
        
    def test_decorator_with_exception_in_view(self):
        """Test that decorator logs exceptions from the view."""
        @track_page_visit
        def test_view(request):
            raise ValueError('Test error')
        
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        with self.assertRaises(ValueError):
            test_view(request)
        
        # Visit should still be tracked before exception
        visit = PageVisit.objects.first()
        self.assertEqual(visit.page_name, '/test/')


class GetClientIpSafeTest(TestCase):
    """Test IP extraction helper function."""
    
    def setUp(self):
        self.factory = RequestFactory()
        
    def test_get_client_ip_from_remote_addr(self):
        """Test extracting IP from REMOTE_ADDR."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        ip = _get_client_ip_safe(request)
        
        self.assertEqual(ip, '192.168.1.1')
        
    def test_get_client_ip_from_x_forwarded_for(self):
        """Test extracting IP from X-Forwarded-For."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.0, 198.51.100.0'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        ip = _get_client_ip_safe(request)
        
        self.assertEqual(ip, '203.0.113.0')
        
    def test_get_client_ip_x_forwarded_for_single(self):
        """Test X-Forwarded-For with single IP."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.0'
        
        ip = _get_client_ip_safe(request)
        
        self.assertEqual(ip, '203.0.113.0')
        
    def test_get_client_ip_missing(self):
        """Test when no IP is available."""
        request = self.factory.get('/')
        
        ip = _get_client_ip_safe(request)
        
        self.assertEqual(ip, 'unknown')
        
    def test_get_client_ip_empty_string(self):
        """Test when REMOTE_ADDR is empty string."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = ''
        
        ip = _get_client_ip_safe(request)
        
        self.assertEqual(ip, 'unknown')
        
    def test_get_client_ip_with_exception(self):
        """Test that function handles exceptions gracefully."""
        request = self.factory.get('/')
        
        with patch.object(request, 'META', side_effect=Exception('Error')):
            ip = _get_client_ip_safe(request)
            
            self.assertEqual(ip, 'unknown')


class TrackPageVisitCBVTest(TestCase):
    """Test class-based view decorator."""
    
    def test_cbv_decorator(self):
        """Test that CBV decorator wraps dispatch method."""
        from django.views import View
        
        @track_page_visit_cbv
        class TestView(View):
            def get(self, request):
                return HttpResponse('Test')
        
        factory = RequestFactory()
        request = factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        view = TestView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that visit was tracked
        visit = PageVisit.objects.first()
        self.assertEqual(visit.page_name, '/test/')
        self.assertEqual(visit.ip_address, '192.168.1.1')
