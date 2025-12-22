from djstripe.models import Subscription
from django.db.models.signals import post_save
from django.dispatch import receiver
from actions.models import Action


@receiver(post_save, sender=Subscription)
def handle_customer_subscription(sender, instance, created, **kwargs):
    subscription = instance
    customer = subscription.customer
    
    if customer and customer.subscriber:
        subscription_metadata = customer.subscriber.get_subscription_metadata(force_refresh=True)
        Action.objects.filter(owner=customer.subscriber).update(
            interval=subscription_metadata['monitor_interval']
        )