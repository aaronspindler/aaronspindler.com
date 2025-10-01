"""
Tests for RequestFingerprintMiddleware.
"""
from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from django.core.exceptions import MiddlewareNotUsed
from unittest.mock import patch, MagicMock

from utils.middleware import RequestFingerprintMiddleware
from utils.models import RequestFingerprint


class RequestFingerprintMiddlewareTest(TestCase):
    """Test request fingerprint middleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=HttpResponse('Test'))
        
    def test_middleware_initialization(self):
        """Test middleware initialization."""
        middleware = RequestFingerprintMiddleware(self.get_response)
        self.assertIsNotNone(middleware)
        
    @patch('utils.middleware.logger')
    def test_middleware_initialization_error(self, mock_logger):
        """Test middleware handles initialization errors."""
        mock_logger.debug.side_effect = Exception('Logger error')
        mock_logger.error.side_effect = None
        
        with self.assertRaises(MiddlewareNotUsed):
            RequestFingerprintMiddleware(self.get_response)
    
    def test_process_request_creates_fingerprint(self):
        """Test that middleware creates a fingerprint for normal requests."""
        middleware = RequestFingerprintMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        request.META['HTTP_ACCEPT'] = 'text/html'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = MagicMock(is_authenticated=False)
        
        # Clear any existing fingerprints
        RequestFingerprint.objects.all().delete()
        
        result = middleware.process_request(request)
        
        # Should return None to continue processing
        self.assertIsNone(result)
        
        # Should create a fingerprint
        self.assertEqual(RequestFingerprint.objects.count(), 1)
        
        # Should attach fingerprint to request
        self.assertTrue(hasattr(request, 'fingerprint'))
        self.assertIsInstance(request.fingerprint, RequestFingerprint)
    
    def test_process_request_skips_static_paths(self):
        """Test that middleware skips static file paths."""
        middleware = RequestFingerprintMiddleware(self.get_response)
        
        skip_paths = [
            '/static/css/style.css',
            '/media/images/photo.jpg',
            '/favicon.ico',
            '/robots.txt',
            '/health',
            '/admin/jsi18n/',
        ]
        
        for path in skip_paths:
            RequestFingerprint.objects.all().delete()
            
            request = self.factory.get(path)
            request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
            request.META['HTTP_ACCEPT'] = 'text/html'
            request.META['REMOTE_ADDR'] = '192.168.1.1'
            request.user = MagicMock(is_authenticated=False)
            
            middleware.process_request(request)
            
            # Should not create fingerprint for skipped paths
            self.assertEqual(RequestFingerprint.objects.count(), 0, f"Path {path} should be skipped")
    
    def test_process_request_tracks_normal_paths(self):
        """Test that middleware tracks normal paths."""
        middleware = RequestFingerprintMiddleware(self.get_response)
        
        normal_paths = [
            '/',
            '/blog/',
            '/about/',
            '/contact/',
        ]
        
        for path in normal_paths:
            RequestFingerprint.objects.all().delete()
            
            request = self.factory.get(path)
            request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
            request.META['HTTP_ACCEPT'] = 'text/html'
            request.META['REMOTE_ADDR'] = '192.168.1.1'
            request.user = MagicMock(is_authenticated=False)
            
            middleware.process_request(request)
            
            # Should create fingerprint for normal paths
            self.assertEqual(RequestFingerprint.objects.count(), 1, f"Path {path} should be tracked")
    
    @patch('utils.middleware.logger')
    def test_process_request_logs_suspicious(self, mock_logger):
        """Test that middleware logs suspicious requests."""
        middleware = RequestFingerprintMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'curl/7.68.0'
        request.META['HTTP_ACCEPT'] = '*/*'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = MagicMock(is_authenticated=False)
        
        RequestFingerprint.objects.all().delete()
        
        middleware.process_request(request)
        
        # Should create fingerprint
        self.assertEqual(RequestFingerprint.objects.count(), 1)
        
        # Should mark as suspicious
        fingerprint = RequestFingerprint.objects.first()
        self.assertTrue(fingerprint.is_suspicious)
        
        # Should log warning
        mock_logger.warning.assert_called_once()
        warning_message = mock_logger.warning.call_args[0][0]
        self.assertIn('Suspicious request detected', warning_message)
        self.assertIn('curl', warning_message)
    
    @patch('utils.middleware.logger')
    def test_process_request_handles_errors_gracefully(self, mock_logger):
        """Test that middleware doesn't block requests if fingerprinting fails."""
        middleware = RequestFingerprintMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        request.META['HTTP_ACCEPT'] = 'text/html'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = MagicMock(is_authenticated=False)
        
        # Mock create_from_request to raise an exception
        with patch('utils.models.RequestFingerprint.create_from_request', side_effect=Exception('DB error')):
            result = middleware.process_request(request)
        
        # Should return None to continue processing
        self.assertIsNone(result)
        
        # Should log error
        mock_logger.error.assert_called_once()
        error_message = mock_logger.error.call_args[0][0]
        self.assertIn('Error creating request fingerprint', error_message)
    
    def test_fingerprint_attached_to_request(self):
        """Test that fingerprint is attached to request object."""
        middleware = RequestFingerprintMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        request.META['HTTP_ACCEPT'] = 'text/html'
        request.META['REMOTE_ADDR'] = '10.0.0.1'
        request.user = MagicMock(is_authenticated=False)
        
        RequestFingerprint.objects.all().delete()
        
        middleware.process_request(request)
        
        # Fingerprint should be attached to request
        self.assertTrue(hasattr(request, 'fingerprint'))
        self.assertEqual(request.fingerprint.ip_address, '10.0.0.1')
        self.assertEqual(request.fingerprint.path, '/test/')
    
    def test_middleware_with_authenticated_user(self):
        """Test that middleware associates fingerprint with authenticated user."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        middleware = RequestFingerprintMiddleware(self.get_response)
        
        request = self.factory.get('/test/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        request.META['HTTP_ACCEPT'] = 'text/html'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = user
        
        RequestFingerprint.objects.all().delete()
        
        middleware.process_request(request)
        
        # Should create fingerprint associated with user
        fingerprint = RequestFingerprint.objects.first()
        self.assertEqual(fingerprint.user, user)
    
    def test_middleware_multiple_requests(self):
        """Test that middleware creates separate fingerprints for multiple requests."""
        middleware = RequestFingerprintMiddleware(self.get_response)
        
        RequestFingerprint.objects.all().delete()
        
        # Make 3 different requests
        for i in range(3):
            request = self.factory.get(f'/test/{i}/')
            request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
            request.META['HTTP_ACCEPT'] = 'text/html'
            request.META['REMOTE_ADDR'] = '192.168.1.1'
            request.user = MagicMock(is_authenticated=False)
            
            middleware.process_request(request)
        
        # Should create 3 separate fingerprints
        self.assertEqual(RequestFingerprint.objects.count(), 3)

