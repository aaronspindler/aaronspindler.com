"""
Comprehensive tests for Utils app Celery tasks.

This module tests all Celery tasks in the utils app, including email sending,
SMS messaging, and Lighthouse audit scheduling.
"""

from unittest.mock import ANY, MagicMock, patch

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from utils.models import Email, NotificationConfig, TextMessage
from utils.tasks import get_notification_config, run_lighthouse_audit, send_email, send_text_message

User = get_user_model()


class NotificationConfigTestMixin:
    """Mixin for tests that need notification configuration."""

    def create_notification_config(self, emails_enabled=True, text_messages_enabled=True):
        """Create a notification configuration."""
        return NotificationConfig.objects.create(
            emails_enabled=emails_enabled,
            text_messages_enabled=text_messages_enabled,
        )


class GetNotificationConfigTest(TestCase):
    """Tests for get_notification_config utility function."""

    def test_get_notification_config_returns_first_config(self):
        """Test that get_notification_config returns the first config."""
        config1 = NotificationConfig.objects.create(
            emails_enabled=True,
            text_messages_enabled=False,
        )
        # Create a second config that should not be returned
        NotificationConfig.objects.create(
            emails_enabled=False,
            text_messages_enabled=True,
        )

        result = get_notification_config()

        expected = config1
        actual = result
        message = f"Expected first config {expected}, got {actual}"
        self.assertEqual(actual, expected, message)

    def test_get_notification_config_returns_none_if_no_config(self):
        """Test that get_notification_config returns None if no config exists."""
        result = get_notification_config()

        expected = None
        actual = result
        message = f"Expected None when no config exists, got {actual}"
        self.assertEqual(actual, expected, message)


class SendEmailTaskTest(TestCase, NotificationConfigTestMixin):
    """Tests for send_email Celery task."""

    def setUp(self):
        """Set up test data."""
        self.config = self.create_notification_config()
        self.email = Email.objects.create(
            recipient="test@example.com",
            subject="Test Subject",
            template="notification",
            parameters='{"name": "Test User"}',
        )

    @patch("utils.tasks.render_to_string")
    @patch("utils.tasks.send_mail")
    def test_send_email_success(self, mock_send_mail, mock_render):
        """Test successful email sending."""
        # Mock template rendering
        mock_render.side_effect = [
            "Text body content",  # .txt template
            "HTML body content",  # .html template
        ]

        # Execute the task
        send_email(self.email.pk)

        # Verify send_mail was called with correct arguments
        mock_send_mail.assert_called_once_with(
            "Test Subject",
            "Text body content",
            settings.DEFAULT_FROM_EMAIL,
            ["test@example.com"],
            html_message="HTML body content",
            fail_silently=True,
        )

        # Verify email was marked as sent
        self.email.refresh_from_db()
        self.assertIsNotNone(self.email.sent)

        actual_text = self.email.text_body
        expected_text = "Text body content"
        message = f"Expected text body '{expected_text}', got '{actual_text}'"
        self.assertEqual(actual_text, expected_text, message)

        actual_html = self.email.html_body
        expected_html = "HTML body content"
        message = f"Expected HTML body '{expected_html}', got '{actual_html}'"
        self.assertEqual(actual_html, expected_html, message)

    def test_send_email_when_emails_disabled(self):
        """Test that email is not sent when emails are disabled."""
        self.config.emails_enabled = False
        self.config.save()

        result = send_email(self.email.pk)

        expected = False
        actual = result
        message = "Task should return False when emails are disabled"
        self.assertEqual(actual, expected, message)

        # Verify email was not marked as sent
        self.email.refresh_from_db()
        self.assertIsNone(self.email.sent)

    def test_send_email_when_already_sent(self):
        """Test that email is not resent if already sent."""
        self.email.sent = timezone.now()
        self.email.save()

        result = send_email(self.email.pk)

        expected = False
        actual = result
        message = "Task should return False when email already sent"
        self.assertEqual(actual, expected, message)

    @patch("utils.tasks.render_to_string")
    def test_send_email_with_template_rendering(self, mock_render):
        """Test that templates are rendered with correct parameters."""
        mock_render.side_effect = ["Text content", "HTML content"]

        send_email(self.email.pk)

        # Verify render_to_string was called with correct template names
        calls = mock_render.call_args_list

        first_call_template = calls[0][0][0]
        expected = "emails/notification.txt"
        actual = first_call_template
        message = f"Expected text template '{expected}', got '{actual}'"
        self.assertEqual(actual, expected, message)

        second_call_template = calls[1][0][0]
        expected = "emails/notification.html"
        actual = second_call_template
        message = f"Expected HTML template '{expected}', got '{actual}'"
        self.assertEqual(actual, expected, message)

    @patch("utils.tasks.send_mail")
    def test_send_email_with_no_config(self, mock_send_mail):
        """Test that email is not sent when no config exists."""
        NotificationConfig.objects.all().delete()

        # This should raise an error since get_notification_config returns None
        with self.assertRaises(AttributeError):
            send_email(self.email.pk)

        # Verify send_mail was not called
        mock_send_mail.assert_not_called()

    @patch("utils.tasks.render_to_string")
    @patch("utils.tasks.send_mail")
    def test_send_email_updates_timestamp(self, mock_send_mail, mock_render):
        """Test that sent timestamp is updated correctly."""
        mock_render.side_effect = ["Text", "HTML"]

        # Capture time before sending
        time_before = timezone.now()

        send_email(self.email.pk)

        # Capture time after sending
        time_after = timezone.now()

        self.email.refresh_from_db()
        self.assertIsNotNone(self.email.sent)
        self.assertGreaterEqual(self.email.sent, time_before)
        self.assertLessEqual(self.email.sent, time_after)

    def test_send_email_with_invalid_pk(self):
        """Test that task handles invalid email PK gracefully."""
        invalid_pk = 99999

        with self.assertRaises(Email.DoesNotExist):
            send_email(invalid_pk)

    @patch("utils.tasks.send_mail")
    def test_send_email_handles_send_mail_exception(self, mock_send_mail):
        """Test that email sending continues even if send_mail fails."""
        # Since fail_silently=True, exceptions should be caught
        mock_send_mail.side_effect = Exception("SMTP error")

        # Should not raise exception due to fail_silently=True
        send_email(self.email.pk)

        # Email should still be marked as sent
        self.email.refresh_from_db()
        self.assertIsNotNone(self.email.sent)


class SendTextMessageTaskTest(TestCase, NotificationConfigTestMixin):
    """Tests for send_text_message Celery task."""

    def setUp(self):
        """Set up test data."""
        self.config = self.create_notification_config()
        self.text_message = TextMessage.objects.create(
            recipient="+15555551234",
            template="notification",
            parameters='{"code": "123456"}',
            message="",
        )

    @patch("utils.tasks.boto3.client")
    @patch("utils.tasks.render_to_string")
    def test_send_text_message_success(self, mock_render, mock_boto_client):
        """Test successful SMS sending."""
        # Mock template rendering
        mock_render.return_value = "Your code is 123456"

        # Mock SNS client
        mock_sns = MagicMock()
        mock_boto_client.return_value = mock_sns

        # Execute the task
        send_text_message(self.text_message.pk)

        # Verify boto3 client was created with correct parameters
        mock_boto_client.assert_called_once_with(
            "sns",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name="us-east-1",
        )

        # Verify SNS publish was called
        mock_sns.publish.assert_called_once_with(
            PhoneNumber="+15555551234",
            Message="Your code is 123456",
        )

        # Verify text message was updated
        self.text_message.refresh_from_db()
        self.assertIsNotNone(self.text_message.sent)

        actual_message = self.text_message.message
        expected_message = "Your code is 123456"
        message = f"Expected message '{expected_message}', got '{actual_message}'"
        self.assertEqual(actual_message, expected_message, message)

    def test_send_text_message_when_text_messages_disabled(self):
        """Test that SMS is not sent when text messages are disabled."""
        self.config.text_messages_enabled = False
        self.config.save()

        result = send_text_message(self.text_message.pk)

        expected = False
        actual = result
        message = "Task should return False when text messages are disabled"
        self.assertEqual(actual, expected, message)

        # Verify message was not sent
        self.text_message.refresh_from_db()
        self.assertIsNone(self.text_message.sent)

    def test_send_text_message_when_already_sent(self):
        """Test that SMS is not resent if already sent."""
        self.text_message.sent = timezone.now()
        self.text_message.save()

        result = send_text_message(self.text_message.pk)

        expected = False
        actual = result
        message = "Task should return False when message already sent"
        self.assertEqual(actual, expected, message)

    @patch("utils.tasks.render_to_string")
    def test_send_text_message_template_rendering(self, mock_render):
        """Test that SMS template is rendered with correct parameters."""
        mock_render.return_value = "Test message"

        with patch("utils.tasks.boto3.client"):
            send_text_message(self.text_message.pk)

        # Verify render_to_string was called with correct template
        mock_render.assert_called_once_with(
            "sms/notification.txt",
            self.text_message.get_parameters(),
        )

    @patch("utils.tasks.boto3.client")
    def test_send_text_message_with_sns_error(self, mock_boto_client):
        """Test handling of AWS SNS errors."""
        # Mock SNS client to raise an error
        mock_sns = MagicMock()
        mock_sns.publish.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameter", "Message": "Invalid phone number"}},
            "Publish",
        )
        mock_boto_client.return_value = mock_sns

        # This should raise the ClientError
        with self.assertRaises(ClientError):
            send_text_message(self.text_message.pk)

        # Verify message was not marked as sent
        self.text_message.refresh_from_db()
        self.assertIsNone(self.text_message.sent)

    @patch("utils.tasks.boto3.client")
    def test_send_text_message_with_boto_error(self, mock_boto_client):
        """Test handling of BotoCore errors."""
        mock_boto_client.side_effect = BotoCoreError()

        with self.assertRaises(BotoCoreError):
            send_text_message(self.text_message.pk)

        # Verify message was not marked as sent
        self.text_message.refresh_from_db()
        self.assertIsNone(self.text_message.sent)

    def test_send_text_message_with_invalid_pk(self):
        """Test that task handles invalid message PK gracefully."""
        invalid_pk = 99999

        with self.assertRaises(TextMessage.DoesNotExist):
            send_text_message(invalid_pk)

    @patch("utils.tasks.boto3.client")
    @patch("utils.tasks.render_to_string")
    def test_send_text_message_updates_timestamp(self, mock_render, mock_boto_client):
        """Test that sent timestamp is updated correctly."""
        mock_render.return_value = "Message"
        mock_boto_client.return_value = MagicMock()

        # Capture time before sending
        time_before = timezone.now()

        send_text_message(self.text_message.pk)

        # Capture time after sending
        time_after = timezone.now()

        self.text_message.refresh_from_db()
        self.assertIsNotNone(self.text_message.sent)
        self.assertGreaterEqual(self.text_message.sent, time_before)
        self.assertLessEqual(self.text_message.sent, time_after)

    @patch("utils.tasks.boto3.client")
    def test_send_text_message_with_empty_recipient(self, mock_boto_client):
        """Test sending SMS with empty recipient."""
        self.text_message.recipient = ""
        self.text_message.save()

        mock_sns = MagicMock()
        mock_boto_client.return_value = mock_sns

        send_text_message(self.text_message.pk)

        # Verify SNS publish was called with empty phone number
        mock_sns.publish.assert_called_once_with(
            PhoneNumber="",
            Message=ANY,
        )


class RunLighthouseAuditTaskTest(TestCase):
    """Tests for run_lighthouse_audit Celery task."""

    @patch("utils.tasks.call_command")
    @patch("utils.tasks.lighthouse_log")
    def test_run_lighthouse_audit_success(self, mock_log, mock_call_command):
        """Test successful Lighthouse audit execution."""
        # Execute the task
        run_lighthouse_audit()

        # Verify management command was called
        mock_call_command.assert_called_once_with("run_lighthouse_audit")

        # Verify logging
        mock_log.info.assert_any_call("Starting scheduled Lighthouse audit for https://aaronspindler.com...")
        mock_log.info.assert_any_call("Lighthouse audit completed successfully")
        mock_log.error.assert_not_called()

    @patch("utils.tasks.call_command")
    @patch("utils.tasks.lighthouse_log")
    def test_run_lighthouse_audit_failure(self, mock_log, mock_call_command):
        """Test Lighthouse audit execution with failure."""
        # Mock command to raise an exception
        mock_call_command.side_effect = CommandError("Lighthouse command failed")

        # Execute the task - should raise the exception
        with self.assertRaises(CommandError):
            run_lighthouse_audit()

        # Verify error logging
        mock_log.error.assert_called_once()
        error_message = mock_log.error.call_args[0][0]
        self.assertIn("Lighthouse audit failed", error_message)
        self.assertIn("Lighthouse command failed", error_message)

    @patch("utils.tasks.call_command")
    @patch("utils.tasks.lighthouse_log")
    def test_run_lighthouse_audit_with_generic_exception(self, mock_log, mock_call_command):
        """Test Lighthouse audit with generic exception."""
        # Mock command to raise a generic exception
        mock_call_command.side_effect = Exception("Unexpected error")

        # Execute the task - should raise the exception
        with self.assertRaises(Exception):
            run_lighthouse_audit()

        # Verify error logging
        mock_log.error.assert_called_once()
        error_message = mock_log.error.call_args[0][0]
        self.assertIn("Lighthouse audit failed", error_message)
        self.assertIn("Unexpected error", error_message)

    @patch("utils.tasks.call_command")
    def test_run_lighthouse_audit_calls_correct_command(self, mock_call_command):
        """Test that the correct management command is called."""
        run_lighthouse_audit()

        # Verify the exact command name
        command_name = mock_call_command.call_args[0][0]
        expected = "run_lighthouse_audit"
        actual = command_name
        message = f"Expected command '{expected}', got '{actual}'"
        self.assertEqual(actual, expected, message)


class CeleryTaskIntegrationTest(TestCase, NotificationConfigTestMixin):
    """Integration tests for Celery tasks."""

    def setUp(self):
        """Set up test data."""
        self.config = self.create_notification_config()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_email_task_as_celery_task(self):
        """Test send_email works as a Celery task."""
        email = Email.objects.create(
            recipient="celery@test.com",
            subject="Celery Test",
            template="notification",
        )

        # Call the task using delay (Celery method)
        result = send_email.delay(email.pk)

        # In ALWAYS_EAGER mode, task executes immediately
        self.assertIsNotNone(result)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("utils.tasks.boto3.client")
    def test_text_message_task_as_celery_task(self, mock_boto):
        """Test send_text_message works as a Celery task."""
        mock_boto.return_value = MagicMock()

        text_message = TextMessage.objects.create(
            recipient="+15555551234",
            template="notification",
            message="",
        )

        # Call the task using delay (Celery method)
        result = send_text_message.delay(text_message.pk)

        # In ALWAYS_EAGER mode, task executes immediately
        self.assertIsNotNone(result)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch("utils.tasks.call_command")
    def test_lighthouse_task_as_celery_task(self, mock_call_command):
        """Test run_lighthouse_audit works as a Celery task."""
        # Call the task using delay (Celery method)
        result = run_lighthouse_audit.delay()

        # In ALWAYS_EAGER mode, task executes immediately
        self.assertIsNotNone(result)
        mock_call_command.assert_called_once()

    def test_multiple_notifications_config(self):
        """Test that only the first config is used when multiple exist."""
        # Create additional configs
        NotificationConfig.objects.create(
            emails_enabled=False,
            text_messages_enabled=False,
        )
        NotificationConfig.objects.create(
            emails_enabled=False,
            text_messages_enabled=False,
        )

        # get_notification_config should return the first one
        config = get_notification_config()

        expected = self.config
        actual = config
        message = f"Should return first config {expected}, got {actual}"
        self.assertEqual(actual, expected, message)

    @patch("utils.tasks.render_to_string")
    @patch("utils.tasks.send_mail")
    def test_email_task_with_complex_parameters(self, mock_send_mail, mock_render):
        """Test email sending with complex parameters."""
        mock_render.side_effect = ["Text", "HTML"]

        # Create email with complex parameters
        email = Email.objects.create(
            recipient="complex@test.com",
            subject="Complex Test",
            template="notification",
            parameters='{"user": {"name": "John", "id": 123}, "items": [1, 2, 3]}',
        )

        send_email(email.pk)

        # Verify email was sent
        mock_send_mail.assert_called_once()
        email.refresh_from_db()
        self.assertIsNotNone(email.sent)


class TaskPerformanceTest(TestCase, NotificationConfigTestMixin):
    """Performance tests for Celery tasks."""

    def setUp(self):
        """Set up test data."""
        self.config = self.create_notification_config()

    @patch("utils.tasks.send_mail")
    def test_bulk_email_sending_performance(self, mock_send_mail):
        """Test performance of sending multiple emails."""
        # Create multiple emails
        emails = []
        for i in range(50):
            email = Email.objects.create(
                recipient=f"user{i}@test.com",
                subject=f"Test {i}",
                template="notification",
            )
            emails.append(email)

        # Send all emails
        for email in emails:
            send_email(email.pk)

        # Verify all were processed
        call_count = mock_send_mail.call_count
        expected = 50
        actual = call_count
        message = f"Expected {expected} emails sent, got {actual}"
        self.assertEqual(actual, expected, message)

        # Verify all emails marked as sent
        unsent_count = Email.objects.filter(sent__isnull=True).count()
        expected = 0
        actual = unsent_count
        message = f"Expected {expected} unsent emails, found {actual}"
        self.assertEqual(actual, expected, message)

    @patch("utils.tasks.boto3.client")
    def test_bulk_sms_sending_performance(self, mock_boto):
        """Test performance of sending multiple SMS messages."""
        mock_sns = MagicMock()
        mock_boto.return_value = mock_sns

        # Create multiple text messages
        messages = []
        for i in range(20):
            msg = TextMessage.objects.create(
                recipient=f"+1555555{i:04d}",
                template="notification",
                message="",
            )
            messages.append(msg)

        # Send all messages
        for msg in messages:
            send_text_message(msg.pk)

        # Verify all were processed
        call_count = mock_sns.publish.call_count
        expected = 20
        actual = call_count
        message = f"Expected {expected} SMS sent, got {actual}"
        self.assertEqual(actual, expected, message)


class TaskErrorHandlingTest(TestCase, NotificationConfigTestMixin):
    """Error handling tests for Celery tasks."""

    def setUp(self):
        """Set up test data."""
        self.config = self.create_notification_config()

    @patch("utils.tasks.render_to_string")
    def test_email_task_with_template_error(self, mock_render):
        """Test email task handles template rendering errors."""
        mock_render.side_effect = Exception("Template not found")

        email = Email.objects.create(
            recipient="error@test.com",
            subject="Error Test",
            template="nonexistent",
        )

        # Should raise the template error
        with self.assertRaises(Exception):
            send_email(email.pk)

        # Email should not be marked as sent
        email.refresh_from_db()
        self.assertIsNone(email.sent)

    @patch("utils.tasks.render_to_string")
    @patch("utils.tasks.boto3.client")
    def test_text_message_task_with_template_error(self, mock_boto, mock_render):
        """Test SMS task handles template rendering errors."""
        mock_render.side_effect = Exception("Template not found")
        mock_boto.return_value = MagicMock()

        text_message = TextMessage.objects.create(
            recipient="+15555551234",
            template="nonexistent",
            message="",
        )

        # Should raise the template error
        with self.assertRaises(Exception):
            send_text_message(text_message.pk)

        # Message should not be marked as sent
        text_message.refresh_from_db()
        self.assertIsNone(text_message.sent)
