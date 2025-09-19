from django.contrib.auth.models import AnonymousUser


class SubscriptionMetadataMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.subscription_metadata = None
        if not isinstance(request.user, AnonymousUser):
            request.subscription_metadata = request.user.get_subscription_metadata()
        response = self.get_response(request)

        return response
