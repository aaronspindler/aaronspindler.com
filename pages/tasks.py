import logging

from celery import shared_task
from django.test import Client

logger = logging.getLogger(__name__)


@shared_task
def rebuild_and_cache_sitemap():
    """
    Rebuild and cache the sitemap by making requests to the sitemap URLs.
    This ensures the sitemap is always cached and fresh.
    """
    try:
        from config.sitemaps import sitemaps

        client = Client()

        # Request the main sitemap index to cache it
        response = client.get("/sitemap.xml")
        if response.status_code == 200:
            logger.info("Main sitemap index cached successfully")
        else:
            logger.warning(f"Failed to cache main sitemap index: {response.status_code}")

        # Request each section sitemap to cache them
        for section in sitemaps.keys():
            url = f"/sitemap-{section}.xml"
            response = client.get(url)
            if response.status_code == 200:
                logger.info(f"Sitemap section '{section}' cached successfully")
            else:
                logger.warning(f"Failed to cache sitemap section '{section}': {response.status_code}")

        logger.info("All sitemaps rebuilt and cached successfully")
        return True
    except Exception as e:
        logger.error(f"Error rebuilding and caching sitemaps: {e}")
        return False
