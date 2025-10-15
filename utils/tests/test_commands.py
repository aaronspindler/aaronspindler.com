"""
Tests for management commands.
"""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from utils.models import RequestFingerprint


class RemoveLocalFingerprintsCommandTest(TestCase):
    """Test the remove_local_fingerprints management command."""

    def setUp(self):
        """Create test fingerprint records."""
        RequestFingerprint.objects.all().delete()

        # Create local IP fingerprints
        self.local_ips = [
            "127.0.0.1",
            "10.0.0.1",
            "192.168.1.1",
            "172.16.0.1",
        ]

        # Create public IP fingerprints
        self.public_ips = [
            "8.8.8.8",
            "1.1.1.1",
            "203.0.113.1",
        ]

        # Create fingerprints for local IPs
        for ip in self.local_ips:
            RequestFingerprint.objects.create(
                fingerprint=f"test-fp-{ip}",
                fingerprint_no_ip=f"test-fp-no-ip-{ip}",
                ip_address=ip,
                method="GET",
                path="/test/",
                user_agent="TestAgent",
            )

        # Create fingerprints for public IPs
        for ip in self.public_ips:
            RequestFingerprint.objects.create(
                fingerprint=f"test-fp-{ip}",
                fingerprint_no_ip=f"test-fp-no-ip-{ip}",
                ip_address=ip,
                method="GET",
                path="/test/",
                user_agent="TestAgent",
            )

    def test_command_dry_run(self):
        """Test that dry-run mode doesn't delete records."""
        initial_count = RequestFingerprint.objects.count()
        local_count = RequestFingerprint.objects.filter(ip_address__in=self.local_ips).count()

        out = StringIO()
        call_command("remove_local_fingerprints", "--dry-run", stdout=out)
        output = out.getvalue()

        # No records should be deleted
        self.assertEqual(RequestFingerprint.objects.count(), initial_count)

        # Output should indicate dry-run mode
        self.assertIn("DRY RUN MODE", output)
        self.assertIn(f"Would delete {local_count} record(s)", output)

    def test_command_deletes_local_ips(self):
        """Test that command deletes local IP fingerprints."""
        initial_count = RequestFingerprint.objects.count()
        local_count = len(self.local_ips)
        public_count = len(self.public_ips)

        out = StringIO()
        call_command("remove_local_fingerprints", stdout=out)
        output = out.getvalue()

        # Local records should be deleted
        self.assertEqual(RequestFingerprint.objects.count(), public_count)

        # Public records should remain
        for ip in self.public_ips:
            self.assertTrue(RequestFingerprint.objects.filter(ip_address=ip).exists())

        # Local records should be gone
        for ip in self.local_ips:
            self.assertFalse(RequestFingerprint.objects.filter(ip_address=ip).exists())

        # Output should show successful deletion
        self.assertIn(f"Successfully deleted {local_count}", output)

    def test_command_with_limit(self):
        """Test that limit parameter works correctly."""
        local_count = len(self.local_ips)
        limit = 2

        out = StringIO()
        call_command("remove_local_fingerprints", "--limit", str(limit), stdout=out)
        output = out.getvalue()

        # Only 'limit' records should be deleted
        remaining_local = RequestFingerprint.objects.filter(ip_address__in=self.local_ips).count()
        self.assertEqual(remaining_local, local_count - limit)

        # Output should show deletion count
        self.assertIn(f"Successfully deleted {limit}", output)
        self.assertIn("records remaining", output)

    def test_command_no_local_ips(self):
        """Test command when no local IPs exist."""
        # Delete all local IP records
        RequestFingerprint.objects.filter(ip_address__in=self.local_ips).delete()

        out = StringIO()
        call_command("remove_local_fingerprints", stdout=out)
        output = out.getvalue()

        # Should report no local IPs found
        self.assertIn("No local IP fingerprints found", output)

    def test_command_shows_statistics(self):
        """Test that command shows IP statistics."""
        out = StringIO()
        call_command("remove_local_fingerprints", "--dry-run", stdout=out)
        output = out.getvalue()

        # Should show unique IP count
        self.assertIn(f"{len(self.local_ips)} unique local/private IP addresses", output)

        # Should show top IPs
        self.assertIn("Top local IPs:", output)
        for ip in self.local_ips:
            self.assertIn(ip, output)

    def test_command_multiple_records_per_ip(self):
        """Test command with multiple records for same IP."""
        # Add more records for one local IP
        test_ip = "127.0.0.1"
        for i in range(5):
            RequestFingerprint.objects.create(
                fingerprint=f"test-fp-{test_ip}-{i}",
                fingerprint_no_ip=f"test-fp-no-ip-{test_ip}-{i}",
                ip_address=test_ip,
                method="GET",
                path=f"/test/{i}/",
                user_agent="TestAgent",
            )

        # Should delete all records with that IP
        initial_127_count = RequestFingerprint.objects.filter(ip_address=test_ip).count()
        self.assertEqual(initial_127_count, 6)  # 1 from setUp + 5 new

        call_command("remove_local_fingerprints")

        # All records with 127.0.0.1 should be deleted
        self.assertEqual(RequestFingerprint.objects.filter(ip_address=test_ip).count(), 0)
