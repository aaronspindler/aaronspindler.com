from django.apps import AppConfig


class PhotosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'photos'
    verbose_name = 'Photo Gallery'
    
    def ready(self):
        """Import signals when the app is ready."""
        import photos.signals