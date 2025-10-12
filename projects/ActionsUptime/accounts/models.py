from django.contrib.auth.models import AbstractUser
from django.db import models
from django.dispatch import receiver
from allauth.account.signals import user_signed_up

from djstripe.models import Customer, Subscription
from djstripe.enums import SubscriptionStatus
from utils.models import NotificationEmail
from django.core.cache import cache


class CustomUser(AbstractUser):
    paid = models.BooleanField(default=False)
    
    def get_customer(self):
        customer = Customer.objects.filter(subscriber=self, deleted=False).first()
        if not customer:
            customer = Customer.objects.filter(email=self.email, deleted=False).first()
        return customer or None
    
    def get_active_subscription(self):
        customer = self.get_customer()
        if customer:
            subscriptions = Subscription.objects.filter(customer=customer, status=SubscriptionStatus.active)
            if subscriptions.exists():
                return subscriptions.first()
        return None
    
    def get_subscription_product(self):
        subscription = self.get_active_subscription()
        if subscription:
            return subscription.plan.product
        return None
    
    def get_subscription_metadata(self, force_refresh=False):
        def _get_parsed_metadata():
            # Default values
            action_types = ['public']
            num_monitors = 3
            monitor_interval = '5M'
            notification_types = ['email']
            private_actions = False
            sms_notifications = False
            endpoint_regions = []
            product = self.get_subscription_product()
            if product:
                # If there is a product, use the metadata from the product
                metadata = product.metadata
                action_types = metadata.get('action_types', '').split(',') if metadata.get('action_types') else ['public']
                num_monitors = metadata.get('num_monitors', 3)
                monitor_interval = metadata.get('monitor_interval', '5M')
                notification_types = metadata.get('notification_types', '').split(',') if metadata.get('notification_types') else ['email']
                private_actions = 'private' in action_types
                sms_notifications = 'sms' in notification_types
                endpoint_regions = metadata.get('endpoint_regions', '').split(',') if metadata.get('endpoint_regions') else []
                
            parsed_metadata = {
                    "action_types": action_types,
                    "num_monitors": num_monitors,
                    "monitor_interval": monitor_interval,
                    "notification_types": notification_types,
                    "private_actions": private_actions,
                    "sms_notifications": sms_notifications,
                    "endpoint_regions": endpoint_regions,
                }
            return parsed_metadata
                    
        cache_key = f'subscription_metadata_{self.id}'
        cached_result = cache.get(cache_key)
        if cached_result is None or force_refresh:
            cached_result = _get_parsed_metadata()
            cache.set(cache_key, cached_result, 5)  # Cache for 5 seconds
        return cached_result
    
    def is_paid(self):
        if self.paid:
            return True
        else:
            subscription = self.get_active_subscription()
            if subscription:
                return True
        return False


    def __str__(self):
        return self.email
    
    @receiver(user_signed_up)
    def allauth_user_signed_up(sender, request, user, **kwargs):
        # Create a NotificationEmail object for the user
        NotificationEmail.objects.create(user=user, email=user.email, verified=True)
        
        # Check if the user has a subscription that is not linked to their account
        customer = Customer.objects.filter(email=user.email, deleted=False).first()
        if customer:
            customer.subscriber = user
            customer.save()