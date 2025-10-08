import logging
from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task
def run_lighthouse_audit():
    """
    Celery task to run a Lighthouse audit of the production site.
    Scheduled to run daily via Celery Beat.
    """
    try:
        logger.info("Starting scheduled Lighthouse audit...")
        call_command('run_lighthouse_audit', '--url', 'https://aaronspindler.com')
        logger.info("Lighthouse audit completed successfully")
    except Exception as e:
        logger.error(f"Lighthouse audit failed: {e}")
        raise

