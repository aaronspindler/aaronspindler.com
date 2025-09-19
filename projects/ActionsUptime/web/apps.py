from django.apps import AppConfig
from django.db.models.signals import post_save


class WebConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'web'
    
    def ready(self):
        from . import signals
        def _lazy_import_subscription(*args, **kwargs):
            from djstripe.models import Subscription
            return Subscription

        post_save.connect(signals.handle_customer_subscription, sender=_lazy_import_subscription())
        
