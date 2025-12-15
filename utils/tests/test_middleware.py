"""
Tests for RequestFingerprintMiddleware.
"""

from unittest.mock import MagicMock, patch

from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from utils.middleware import RequestFingerprintMiddleware
from utils.models import RequestFingerprint


class RequestFingerprintMiddlewareTest(TestCase):
    """Test request fingerprint middleware."""

    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=HttpResponse("Test"))

    def test_process_request_creates_fingerprint(self):
        """Test that middleware creates a fingerprint for normal requests."""
        middleware = RequestFingerprintMiddleware(self.get_response)

        request = self.factory.get("/test/")
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        request.META["HTTP_ACCEPT"] = "text/html"
        request.META["REMOTE_ADDR"] = "8.8.8.8"  # Global IP (Google DNS)
        request.user = MagicMock(is_authenticated=False)

        # Clear any existing fingerprints
        RequestFingerprint.objects.all().delete()

        result = middleware.process_request(request)

        # Should return None to continue processing
        self.assertIsNone(result)

        # Should create a fingerprint
        self.assertEqual(RequestFingerprint.objects.count(), 1)

        # Should attach fingerprint to request
        self.assertTrue(hasattr(request, "fingerprint"))
        self.assertIsInstance(request.fingerprint, RequestFingerprint)

    def test_process_request_skips_static_paths(self):
        """Test that middleware skips static file paths."""
        middleware = RequestFingerprintMiddleware(self.get_response)

        skip_paths = [
            "/static/css/style.css",
            "/media/images/photo.jpg",
            "/favicon.ico",
            "/robots.txt",
            "/health",
            "/admin/jsi18n/",
        ]

        for path in skip_paths:
            RequestFingerprint.objects.all().delete()

            request = self.factory.get(path)
            request.META["HTTP_USER_AGENT"] = "Mozilla/5.0"
            request.META["HTTP_ACCEPT"] = "text/html"
            request.META["REMOTE_ADDR"] = "8.8.8.8"  # Global IP (Google DNS)
            request.user = MagicMock(is_authenticated=False)

            middleware.process_request(request)

            # Should not create fingerprint for skipped paths
            self.assertEqual(RequestFingerprint.objects.count(), 0, f"Path {path} should be skipped")

    @patch("utils.middleware.logger")
    def test_process_request_logs_suspicious(self, mock_logger):
        """Test that middleware logs suspicious requests."""
        middleware = RequestFingerprintMiddleware(self.get_response)

        request = self.factory.get("/test/")
        request.META["HTTP_USER_AGENT"] = "curl/7.68.0"
        request.META["HTTP_ACCEPT"] = "*/*"
        request.META["REMOTE_ADDR"] = "8.8.8.8"  # Global IP (Google DNS)
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
        self.assertIn("Suspicious request detected", warning_message)
        self.assertIn("curl", warning_message)

    @patch("utils.middleware.logger")
    def test_process_request_handles_errors_gracefully(self, mock_logger):
        """Test that middleware doesn't block requests if fingerprinting fails."""
        middleware = RequestFingerprintMiddleware(self.get_response)

        request = self.factory.get("/test/")
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0"
        request.META["HTTP_ACCEPT"] = "text/html"
        request.META["REMOTE_ADDR"] = "8.8.8.8"  # Global IP (Google DNS)
        request.user = MagicMock(is_authenticated=False)

        # Mock create_from_request to raise an exception
        with patch(
            "utils.models.RequestFingerprint.create_from_request",
            side_effect=Exception("DB error"),
        ):
            result = middleware.process_request(request)

        # Should return None to continue processing
        self.assertIsNone(result)

        # Should log error
        mock_logger.error.assert_called_once()
        error_message = mock_logger.error.call_args[0][0]
        self.assertIn("Error creating request fingerprint", error_message)

    def test_middleware_with_authenticated_user(self):
        """Test that middleware associates fingerprint with authenticated user."""
        from django.contrib.auth import get_user_model

        User = get_user_model()

        user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

        middleware = RequestFingerprintMiddleware(self.get_response)

        request = self.factory.get("/test/")
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0"
        request.META["HTTP_ACCEPT"] = "text/html"
        request.META["REMOTE_ADDR"] = "8.8.8.8"  # Global IP (Google DNS)
        request.user = user

        RequestFingerprint.objects.all().delete()

        middleware.process_request(request)

        # Should create fingerprint associated with user
        fingerprint = RequestFingerprint.objects.first()
        self.assertEqual(fingerprint.user, user)

    @patch("utils.middleware.logger")
    def test_process_request_skips_local_ips(self, mock_logger):
        """Test that middleware skips local/private IP addresses."""
        middleware = RequestFingerprintMiddleware(self.get_response)

        local_ips = [
            "127.0.0.1",  # Localhost IPv4
            "::1",  # Localhost IPv6
            "10.0.0.1",  # Private IP (10.0.0.0/8)
            "192.168.1.1",  # Private IP (192.168.0.0/16)
            "172.16.0.1",  # Private IP (172.16.0.0/12)
            "172.31.255.255",  # Private IP (172.16.0.0/12)
        ]

        for ip in local_ips:
            RequestFingerprint.objects.all().delete()

            request = self.factory.get("/test/")
            request.META["HTTP_USER_AGENT"] = "Mozilla/5.0"
            request.META["HTTP_ACCEPT"] = "text/html"
            request.META["REMOTE_ADDR"] = ip
            request.user = MagicMock(is_authenticated=False)

            middleware.process_request(request)

            # Should not create fingerprint for local IPs
            self.assertEqual(RequestFingerprint.objects.count(), 0, f"Local IP {ip} should be skipped")

            # Should log debug message
            debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
            self.assertTrue(
                any(f"Skipping local request from {ip}" in call for call in debug_calls),
                f"Should log skip message for {ip}",
            )
