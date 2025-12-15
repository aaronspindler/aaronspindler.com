import logging

import boto3
from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.core.mail import send_mail
from django.core.management import call_command
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_notification_config():
    NotificationConfig = apps.get_model("utils", "NotificationConfig")
    return NotificationConfig.objects.first()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes between retries
    max_retries=3,
)
def send_email(self, email_pk):
    notification_config = get_notification_config()
    if not notification_config.emails_enabled:
        return False

    Email = apps.get_model("utils", "Email")
    email = Email.objects.get(pk=email_pk)
    if email.sent:
        return False

    parameters = email.get_parameters()
    # check if there is an unsubscribe code associated with this email address
    text_body = render_to_string("emails/{}.txt".format(email.template), parameters)
    html_body = render_to_string("emails/{}.html".format(email.template), parameters)

    emails = [email.recipient]

    send_mail(
        email.subject,
        text_body,
        settings.DEFAULT_FROM_EMAIL,
        emails,
        html_message=html_body,
        fail_silently=True,
    )

    email.text_body = text_body
    email.html_body = html_body
    email.sent = timezone.now()
    email.save()
    return True


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes between retries
    max_retries=3,
)
def send_text_message(self, text_message_pk):
    notification_config = get_notification_config()
    if not notification_config.text_messages_enabled:
        return False

    TextMessage = apps.get_model("utils", "TextMessage")
    text_message = TextMessage.objects.get(pk=text_message_pk)
    if text_message.sent:
        return False

    sns = boto3.client(
        "sns",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name="us-east-1",
    )

    parameters = text_message.get_parameters()
    message = render_to_string("sms/{}.txt".format(text_message.template), parameters)

    sns.publish(PhoneNumber=text_message.recipient, Message=message)

    text_message.message = message
    text_message.sent = timezone.now()
    text_message.save()
    return True


@shared_task
def test_celery_beat():
    """
    Simple test task to verify Celery Beat is working.
    Scheduled to run every minute for testing purposes.
    """
    logger.info("=" * 50)
    logger.info("TEST CELERY BEAT TASK EXECUTED SUCCESSFULLY")
    logger.info(f"Current time: {timezone.now()}")
    logger.info("=" * 50)
    return "Test task completed"


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=1800,  # Max 30 minutes (this is a heavy task)
    max_retries=2,
)
def run_lighthouse_audit(self):
    """
    Celery task to run a Lighthouse audit.
    Scheduled to run daily via Celery Beat.
    """
    url = "https://aaronspindler.com"
    try:
        logger.info(f"Starting scheduled Lighthouse audit for {url}...")
        call_command("run_lighthouse_audit")
        logger.info("Lighthouse audit completed successfully")
    except Exception as e:
        logger.error(f"Lighthouse audit failed: {e}")
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes between retries
    max_retries=3,
)
def geolocate_missing_ips(self):
    """
    Celery task to geolocate IP addresses without geo data.
    Processes up to 200 IPs in batches of 100, with a limit of 2 batches.
    Scheduled to run every 15 minutes via Celery Beat.
    """
    from django.db.models import Q

    from utils.models.security import IPAddress
    from utils.security import geolocate_ips_batch

    try:
        # Find IPs without geo data (null or empty dict)
        missing_geo_ips = IPAddress.objects.filter(Q(geo_data__isnull=True) | Q(geo_data={}))[:200]

        if not missing_geo_ips:
            logger.info("No IP addresses found that need geolocation")
            return "No IPs to geolocate"

        ip_count = len(missing_geo_ips)
        logger.info(f"Starting geolocation for {ip_count} IP addresses...")

        # Extract IP addresses
        ip_addresses = [ip.ip_address for ip in missing_geo_ips]

        # Geolocate in batches (100 IPs per batch, max 2 batches = 200 IPs)
        results = geolocate_ips_batch(ip_addresses, batch_size=100, max_batches=2)

        # Update records with results
        success_count = 0
        for ip_str, geo_data in results.items():
            if geo_data:
                IPAddress.objects.filter(ip_address=ip_str).update(geo_data=geo_data)
                success_count += 1

        logger.info(f"Geolocation task completed: {success_count}/{ip_count} IPs successfully geolocated")
        return f"Geolocated {success_count}/{ip_count} IPs"

    except Exception as e:
        logger.error(f"Geolocation task failed: {e}", exc_info=True)
        raise
