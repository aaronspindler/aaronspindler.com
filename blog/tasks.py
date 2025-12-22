import logging

from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def rebuild_knowledge_graph(self, force_refresh=False):
    from blog.knowledge_graph import build_knowledge_graph

    try:
        graph_data = build_knowledge_graph(force_refresh=force_refresh)
        cache.set("knowledge_graph_data", graph_data, timeout=3600)  # 1 hour cache
        logger.info("Knowledge graph rebuilt and cached successfully")
        return graph_data
    except Exception as e:
        logger.error(f"Error rebuilding knowledge graph: {e}")
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=1800,  # Max 30 minutes (this is a heavy task)
    max_retries=2,
)
def generate_knowledge_graph_screenshot(self):
    from django.core.management import call_command

    try:
        logger.info("Starting knowledge graph screenshot generation task...")
        call_command("generate_knowledge_graph_screenshot", "--url", "https://aaronspindler.com")
        logger.info("Knowledge graph screenshot generated successfully")
        return "screenshot_generated"
    except Exception as e:
        logger.error(f"Error generating knowledge graph screenshot: {e}")
        raise
