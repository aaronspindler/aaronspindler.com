"""
Test file for pages app decorators.

Note: track_page_visit decorator now only logs visits. Actual request tracking
is handled by RequestFingerprintMiddleware in the utils app.
"""
from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from unittest.mock import patch
from pages.decorators import track_page_visit, track_page_visit_cbv


class TrackPageVisitDecoratorTest(TestCase):
    """Test page visit logging decorator."""
    
    def setUp(self):
        self.factory = RequestFactory()
        
    def test_decorator_logs_visit(self):
        """Test that decorator logs page visits."""
        @track_page_visit
        def test_view(request):
            return HttpResponse('Test')
        
        request = self.factory.get('/test-page/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        with patch('pages.decorators.logger') as mock_logger:
            response = test_view(request)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b'Test')
            
            # Check that visit was logged
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args[0][0]
            self.assertIn('/test-page/', log_call)
            self.assertIn('192.168.1.1', log_call)
        
    def test_decorator_handles_logging_error(self):
        """Test that decorator continues even if logging fails."""
        @track_page_visit
        def test_view(request):
            return HttpResponse('Success')
        
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        with patch('pages.decorators.logger') as mock_logger:
            mock_logger.info.side_effect = Exception('Logging error')
            
            response = test_view(request)
            
            # View should still execute successfully
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b'Success')
            
    def test_decorator_sanitizes_inputs(self):
        """Test that decorator sanitizes user inputs to prevent log injection."""
        @track_page_visit
        def test_view(request):
            return HttpResponse('Test')
        
        request = self.factory.get('/test\n/injection\r/')
        request.META['REMOTE_ADDR'] = '192.168.1.1\n'
        request.META['HTTP_USER_AGENT'] = 'Mozilla\n/5.0\r'
        
        with patch('pages.decorators.logger') as mock_logger:
            test_view(request)
            
            # Check that inputs were sanitized
            log_call = mock_logger.info.call_args[0][0]
            self.assertNotIn('\n', log_call)
            self.assertNotIn('\r', log_call)


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
        
        with patch('pages.decorators.logger'):
            view = TestView.as_view()
            response = view(request)
            
            self.assertEqual(response.status_code, 200)
