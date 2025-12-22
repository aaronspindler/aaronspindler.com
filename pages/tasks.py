import logging

from celery import shared_task
from django.test import Client

logger = logging.getLogger(__name__)


@shared_task
def rebuild_and_cache_sitemap():
    try:
        from config.sitemaps import sitemaps

        client = Client()

        response = client.get("/sitemap.xml")
        if response.status_code == 200:
            logger.info("Main sitemap index cached successfully")
        else:
            logger.warning(f"Failed to cache main sitemap index: {response.status_code}")

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
