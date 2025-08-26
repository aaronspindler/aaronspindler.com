from celery import shared_task
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_async_email(self, subject, message, recipient_list):
    """
    Asynchronously send email notifications
    """
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        logger.info(f"Email sent successfully to {recipient_list}")
        return True
    except Exception as exc:
        logger.error(f"Error sending email: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

@shared_task
def clear_cache_key(cache_key):
    """
    Clear a specific cache key
    """
    cache.delete(cache_key)
    logger.info(f"Cache key {cache_key} cleared")
    return True

@shared_task
def process_photo_optimization(photo_id):
    """
    Process photo optimization in the background
    """
    from pages.models import Photo
    try:
        photo = Photo.objects.get(id=photo_id)
        # Your photo optimization logic here
        logger.info(f"Photo {photo_id} optimized successfully")
        return True
    except Photo.DoesNotExist:
        logger.error(f"Photo with id {photo_id} does not exist")
        return False

@shared_task
def generate_sitemap():
    """
    Generate or update the sitemap
    """
    from django.contrib.sitemaps import ping_google
    try:
        # Your sitemap generation logic here
        # Optionally ping Google
        if not settings.DEBUG:
            ping_google('/sitemap.xml')
        logger.info("Sitemap generated successfully")
        return True
    except Exception as e:
        logger.error(f"Error generating sitemap: {e}")
        return False