"""Domain-based URL routing middleware.

This middleware allows serving different Django apps from different domains
within the same Django project, without using django-hosts.

Instead of using ROOT_URLCONF directly, it dynamically sets the URLconf
based on the request's hostname.
"""


class DomainRoutingMiddleware:
    """Middleware to route requests to different URL configurations based on domain."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Process the request and set the appropriate URLconf based on domain."""
        host = request.get_host().split(":")[0].lower()  # Remove port if present

        # Domain to URLconf mapping
        domain_mapping = {
            "omas.coffee": "omas.urls",
            "www.omas.coffee": "omas.urls",
        }

        # Set the URLconf for this request
        if host in domain_mapping:
            request.urlconf = domain_mapping[host]
        # Otherwise, use the default ROOT_URLCONF (config.urls)

        response = self.get_response(request)
        return response
