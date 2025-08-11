from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)

class PagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pages'

    def ready(self):
        """Initialize pages app."""
        # Check if we should clear cache on startup
        if os.getenv('CLEAR_CACHE_ON_STARTUP', '').lower() == 'true':
            try:
                from .knowledge_graph import clear_knowledge_graph_cache
                clear_knowledge_graph_cache()
                logger.info("Knowledge graph cache cleared on startup")
            except Exception as e:
                logger.error(f"Failed to clear knowledge graph cache on startup: {e}")
        
        logger.info("Pages app ready")
