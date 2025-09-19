from djstripe.models import Subscription
from django.db.models.signals import post_save
from django.dispatch import receiver
from actions.models import Action

@receiver(post_save, sender=Subscription)
def handle_customer_subscription(sender, instance, created, **kwargs):
    # Get the subscription from the instance
    subscription = instance
    # Find the customer associated with this subscription
    customer = subscription.customer
    
    if customer and customer.subscriber:
        # get the subscription metadata
        subscription_metadata = customer.subscriber.get_subscription_metadata(force_refresh=True)
        # Update all actions for this user with new metadata in a single query
        Action.objects.filter(owner=customer.subscriber).update(
            interval=subscription_metadata['monitor_interval']
        )