"""
Tests for security utilities.
"""

from django.test import RequestFactory, TestCase

from utils.security import get_client_ip, is_local_ip


class IsLocalIPTest(TestCase):
    """Test the is_local_ip function."""

    def test_localhost_ipv4(self):
        """Test that 127.0.0.1 is identified as local."""
        self.assertTrue(is_local_ip("127.0.0.1"))

    def test_localhost_ipv6(self):
        """Test that ::1 is identified as local."""
        self.assertTrue(is_local_ip("::1"))

    def test_localhost_string(self):
        """Test that 'localhost' string is identified as local."""
        self.assertTrue(is_local_ip("localhost"))

    def test_private_ip_10_network(self):
        """Test that 10.0.0.0/8 network is identified as local."""
        test_ips = ["10.0.0.1", "10.255.255.255", "10.1.2.3"]
        for ip in test_ips:
            self.assertTrue(is_local_ip(ip), f"{ip} should be local")

    def test_private_ip_192_168_network(self):
        """Test that 192.168.0.0/16 network is identified as local."""
        test_ips = ["192.168.0.1", "192.168.1.1", "192.168.255.255"]
        for ip in test_ips:
            self.assertTrue(is_local_ip(ip), f"{ip} should be local")

    def test_private_ip_172_16_to_31_network(self):
        """Test that 172.16.0.0/12 network is identified as local."""
        test_ips = ["172.16.0.1", "172.31.255.255", "172.20.1.1"]
        for ip in test_ips:
            self.assertTrue(is_local_ip(ip), f"{ip} should be local")

    def test_private_ip_172_outside_range(self):
        """Test that 172.x.x.x outside 16-31 range is not local."""
        test_ips = ["172.15.0.1", "172.32.0.1", "172.0.0.1"]
        for ip in test_ips:
            self.assertFalse(is_local_ip(ip), f"{ip} should not be local")

    def test_public_ip_addresses(self):
        """Test that public IP addresses are not identified as local."""
        test_ips = [
            "8.8.8.8",  # Google DNS
            "1.1.1.1",  # Cloudflare DNS
            "203.0.113.1",  # TEST-NET-3 (documentation)
            "198.51.100.1",  # TEST-NET-2 (documentation)
            "93.184.216.34",  # example.com
        ]
        for ip in test_ips:
            self.assertFalse(is_local_ip(ip), f"{ip} should not be local")

    def test_empty_string(self):
        """Test that empty string returns False."""
        self.assertFalse(is_local_ip(""))

    def test_unknown_string(self):
        """Test that 'unknown' returns False."""
        self.assertFalse(is_local_ip("unknown"))

    def test_none_value(self):
        """Test that None returns False."""
        self.assertFalse(is_local_ip(None))


class GetClientIPTest(TestCase):
    """Test the get_client_ip function."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_remote_addr(self):
        """Test extracting IP from REMOTE_ADDR."""
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "203.0.113.1"

        ip = get_client_ip(request)
        self.assertEqual(ip, "203.0.113.1")

    def test_x_forwarded_for_single_ip(self):
        """Test extracting IP from X-Forwarded-For with single IP."""
        request = self.factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1"
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        ip = get_client_ip(request)
        self.assertEqual(ip, "203.0.113.1")

    def test_x_forwarded_for_multiple_ips(self):
        """Test extracting IP from X-Forwarded-For with multiple IPs."""
        request = self.factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1, 198.51.100.1, 192.0.2.1"
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        ip = get_client_ip(request)
        # Should return the first IP (client)
        self.assertEqual(ip, "203.0.113.1")

    def test_x_real_ip(self):
        """Test extracting IP from X-Real-IP."""
        request = self.factory.get("/")
        request.META["HTTP_X_REAL_IP"] = "203.0.113.1"
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        ip = get_client_ip(request)
        self.assertEqual(ip, "203.0.113.1")

    def test_x_forwarded_for_priority(self):
        """Test that X-Forwarded-For takes priority over X-Real-IP."""
        request = self.factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1"
        request.META["HTTP_X_REAL_IP"] = "198.51.100.1"
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        ip = get_client_ip(request)
        self.assertEqual(ip, "203.0.113.1")

    def test_no_ip_available(self):
        """Test fallback when no IP is available."""
        request = self.factory.get("/")
        # Don't set any IP-related headers

        ip = get_client_ip(request)
        self.assertEqual(ip, "unknown")

    def test_whitespace_handling(self):
        """Test that whitespace is properly stripped from IPs."""
        request = self.factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = " 203.0.113.1 , 198.51.100.1 "

        ip = get_client_ip(request)
        self.assertEqual(ip, "203.0.113.1")
