from celery import shared_task
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

@shared_task
def rebuild_knowledge_graph():
    """
    Rebuild the knowledge graph cache periodically.
    
    This task is run by Celery Beat to keep the graph data fresh.
    Caches the result for 1 hour to improve performance.
    """
    from blog.knowledge_graph import KnowledgeGraph
    try:
        graph = KnowledgeGraph()
        graph_data = graph.generate_graph_data()
        cache.set('knowledge_graph_data', graph_data, timeout=3600)  # 1 hour cache
        logger.info("Knowledge graph rebuilt and cached successfully")
        return True
    except Exception as e:
        logger.error(f"Error rebuilding knowledge graph: {e}")
        return False

@shared_task
def generate_knowledge_graph_screenshot():
    """
    Generate a static screenshot of the knowledge graph for faster loading.
    
    This task runs periodically to update the cached screenshot image,
    avoiding the need for dynamic generation on each request.
    """
    from blog.knowledge_graph import KnowledgeGraph
    try:
        graph = KnowledgeGraph()
        screenshot_path = graph.generate_screenshot()
        logger.info(f"Knowledge graph screenshot generated: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        logger.error(f"Error generating knowledge graph screenshot: {e}")
        return None
