from django.urls import path

from .views import home, notifications, roadmap, support, privacy_policy, terms_of_service, subscription_confirmation, billing_portal

urlpatterns = [
    path("", home, name="home"),
    path("subscription-confirm/", subscription_confirmation, name="subscription-confirmation"),
    path("billing-portal/", billing_portal, name="billing-portal"),
    path("notifications", notifications, name="notifications"),
    path("roadmap", roadmap, name="roadmap"),
    path("support", support, name="support"),
    path("privacy-policy", privacy_policy, name="privacy-policy"),
    path("terms-of-service", terms_of_service, name="terms-of-service"),
]
