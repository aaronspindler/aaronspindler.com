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

@shared_task
def update_blog_post_stats(template_name):
    """
    Update blog post statistics (view count, etc.)
    """
    from blog.models import BlogPostView
    try:
        # Your blog post stats update logic here
        logger.info(f"Blog post stats updated for {template_name}")
        return True
    except Exception as e:
        logger.error(f"Error updating blog post stats: {e}")
        return False

@shared_task
def clear_blog_cache():
    """
    Clear all blog-related cache entries
    """
    cache_keys = [
        'knowledge_graph_data',
        'blog_posts_list',
        'blog_categories',
        # Add more cache keys as needed
    ]
    for key in cache_keys:
        cache.delete(key)
    logger.info("Blog cache cleared successfully")
    return True