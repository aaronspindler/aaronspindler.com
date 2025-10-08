from unittest.mock import patch
from django.test import TestCase
from lighthouse_monitor.tasks import run_lighthouse_audit


class LighthouseTaskTests(TestCase):
    """Test cases for Lighthouse Celery tasks."""

    @patch('lighthouse_monitor.tasks.call_command')
    def test_run_lighthouse_audit_task_success(self, mock_call_command):
        """Test that the Celery task calls the management command correctly."""
        run_lighthouse_audit()
        mock_call_command.assert_called_once_with(
            'run_lighthouse_audit',
            '--url',
            'https://aaronspindler.com'
        )

    @patch('lighthouse_monitor.tasks.call_command')
    def test_run_lighthouse_audit_task_failure(self, mock_call_command):
        """Test that the Celery task raises exception on failure."""
        mock_call_command.side_effect = Exception('Audit failed')
        with self.assertRaises(Exception):
            run_lighthouse_audit()

