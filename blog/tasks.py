import logging

from django.core.cache import cache

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def rebuild_knowledge_graph(force_refresh=False):
    """
    Rebuild the knowledge graph cache periodically.

    This task is run by Celery Beat to keep the graph data fresh.
    Caches the result for 1 hour to improve performance.
    """
    from blog.knowledge_graph import build_knowledge_graph

    try:
        graph_data = build_knowledge_graph(force_refresh=force_refresh)
        cache.set("knowledge_graph_data", graph_data, timeout=3600)  # 1 hour cache
        logger.info("Knowledge graph rebuilt and cached successfully")
        return graph_data
    except Exception as e:
        logger.error(f"Error rebuilding knowledge graph: {e}")
        return None


@shared_task
def generate_knowledge_graph_screenshot():
    """
    Generate a static screenshot of the knowledge graph for faster loading.

    This task runs periodically to update the cached screenshot image,
    avoiding the need for dynamic generation on each request.
    """
    try:
        # For now, just return a placeholder since screenshot generation
        # is handled in the view directly
        logger.info("Knowledge graph screenshot generation task called")
        return "screenshot_placeholder"
    except Exception as e:
        logger.error(f"Error generating knowledge graph screenshot: {e}")
        return None
