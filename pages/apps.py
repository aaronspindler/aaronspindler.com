from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class PagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pages'

    def ready(self):
        logger.info("Pages app ready")
