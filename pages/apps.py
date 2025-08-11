from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)

class PagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pages'

    def ready(self):
        """Initialize pages app."""
        logger.info("Pages app ready")
