from celery import shared_task
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

@shared_task
def rebuild_knowledge_graph():
    """
    Rebuild the knowledge graph cache
    """
    from blog.knowledge_graph import KnowledgeGraph
    try:
        graph = KnowledgeGraph()
        graph_data = graph.generate_graph_data()
        # Cache the graph data
        cache.set('knowledge_graph_data', graph_data, timeout=3600)  # Cache for 1 hour
        logger.info("Knowledge graph rebuilt and cached successfully")
        return True
    except Exception as e:
        logger.error(f"Error rebuilding knowledge graph: {e}")
        return False

@shared_task
def generate_knowledge_graph_screenshot():
    """
    Generate knowledge graph screenshot in the background
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
