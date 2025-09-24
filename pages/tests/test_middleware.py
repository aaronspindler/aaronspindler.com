from django.test import TestCase, RequestFactory
from django.http import HttpResponse, Http404
from django.core.exceptions import MiddlewareNotUsed
from unittest.mock import patch, MagicMock
from pages.middleware import RequestLoggingMiddleware
import time


class RequestLoggingMiddlewareTest(TestCase):
    """Test request logging middleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=HttpResponse('Test'))
        
    def test_middleware_initialization(self):
        """Test middleware initialization."""
        middleware = RequestLoggingMiddleware(self.get_response)
        self.assertIsNotNone(middleware)
        
    @patch('pages.middleware.logger')
    def test_middleware_initialization_error(self, mock_logger):
        """Test middleware handles initialization errors."""
        mock_logger.debug.side_effect = Exception('Logger error')
        mock_logger.error.side_effect = None
        
        with self.assertRaises(MiddlewareNotUsed):
            RequestLoggingMiddleware(self.get_response)
            
    @patch('pages.middleware.logger')
    def test_process_request_logging(self, mock_logger):
        """Test that middleware logs request start."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        middleware.process_request(request)
        
        # Check that request was logged
        mock_logger.info.assert_called()
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn('Request started', log_message)
        self.assertIn('GET', log_message)
        self.assertIn('/test/', log_message)
        self.assertIn('192.168.1.1', log_message)
        
        # Check that start time was set
        self.assertTrue(hasattr(request, '_start_time'))
        
    @patch('pages.middleware.logger')
    def test_process_response_logging(self, mock_logger):
        """Test that middleware logs response."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request._start_time = time.time()
        
        response = HttpResponse('Test', status=200)
        
        middleware.process_response(request, response)
        
        # Check that response was logged
        mock_logger.info.assert_called()
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn('Request completed', log_message)
        self.assertIn('Status: 200', log_message)
        self.assertIn('Duration:', log_message)
        self.assertIn('ms', log_message)
        
    @patch('pages.middleware.logger')
    def test_process_response_without_start_time(self, mock_logger):
        """Test response processing without start time."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        # Don't set _start_time
        
        response = HttpResponse('Test')
        
        result = middleware.process_response(request, response)
        
        # Should still return response
        self.assertEqual(result, response)
        
    @patch('pages.middleware.logger')
    def test_process_exception_logging(self, mock_logger):
        """Test that middleware logs exceptions."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request._start_time = time.time()
        
        exception = ValueError('Test error')
        
        middleware.process_exception(request, exception)
        
        # Check that exception was logged
        mock_logger.error.assert_called()
        log_message = mock_logger.error.call_args[0][0]
        self.assertIn('Request failed', log_message)
        self.assertIn('ValueError', log_message)
        self.assertIn('Test error', log_message)
        
    def test_get_client_ip_x_forwarded(self):
        """Test IP extraction from X-Forwarded-For."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.0, 198.51.100.0'
        
        ip = middleware._get_client_ip(request)
        
        self.assertEqual(ip, '203.0.113.0')
        
    def test_get_client_ip_remote_addr(self):
        """Test IP extraction from REMOTE_ADDR."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        ip = middleware._get_client_ip(request)
        
        self.assertEqual(ip, '192.168.1.1')
        
    def test_get_client_ip_missing(self):
        """Test IP extraction when no IP available."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        
        ip = middleware._get_client_ip(request)
        
        self.assertEqual(ip, 'unknown')
        
    @patch('pages.middleware.logger')
    def test_get_client_ip_error_handling(self, mock_logger):
        """Test IP extraction error handling."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = MagicMock()
        request.META.get.side_effect = Exception('META error')
        
        ip = middleware._get_client_ip(request)
        
        self.assertEqual(ip, 'unknown')
        mock_logger.debug.assert_called()
        
    @patch('pages.middleware.logger')
    def test_process_request_error_handling(self, mock_logger):
        """Test error handling in process_request."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        
        # Mock logger to raise exception
        mock_logger.info.side_effect = Exception('Logging error')
        
        result = middleware.process_request(request)
        
        # Should return None and set start time
        self.assertIsNone(result)
        self.assertTrue(hasattr(request, '_start_time'))
        
    @patch('pages.middleware.logger')
    def test_process_response_error_handling(self, mock_logger):
        """Test error handling in process_response."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        response = HttpResponse('Test')
        
        # Mock logger to raise exception
        mock_logger.info.side_effect = Exception('Logging error')
        
        result = middleware.process_response(request, response)
        
        # Should still return response
        self.assertEqual(result, response)
        
    @patch('pages.middleware.logger')
    def test_process_exception_error_handling(self, mock_logger):
        """Test error handling in process_exception."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        exception = ValueError('Test')
        
        # Mock logger to raise exception on first call
        mock_logger.error.side_effect = [Exception('Logging error'), None]
        
        result = middleware.process_exception(request, exception)
        
        # Should return None
        self.assertIsNone(result)
        # Should attempt fallback logging
        self.assertEqual(mock_logger.error.call_count, 2)
        
    @patch('pages.middleware.logger')
    def test_timing_calculation(self, mock_logger):
        """Test request duration calculation."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Set start time to 100ms ago
        request._start_time = time.time() - 0.1
        
        response = HttpResponse('Test')
        middleware.process_response(request, response)
        
        # Check that duration was calculated
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn('Duration:', log_message)
        
        # Extract duration from log
        import re
        match = re.search(r'Duration: ([\d.]+)ms', log_message)
        self.assertIsNotNone(match)
        duration = float(match.group(1))
        
        # Duration should be around 100ms
        self.assertGreater(duration, 90)
        self.assertLess(duration, 110)
        
    def test_middleware_preserves_request_attributes(self):
        """Test that middleware doesn't interfere with request attributes."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.custom_attr = 'test_value'
        
        middleware.process_request(request)
        
        # Custom attribute should still be present
        self.assertEqual(request.custom_attr, 'test_value')
        
    def test_middleware_preserves_response(self):
        """Test that middleware doesn't modify response."""
        middleware = RequestLoggingMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        response = HttpResponse('Test content', status=201)
        response['Custom-Header'] = 'test'
        
        result = middleware.process_response(request, response)
        
        # Response should be unchanged
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.content, b'Test content')
        self.assertEqual(result['Custom-Header'], 'test')
