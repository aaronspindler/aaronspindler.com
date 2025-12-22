class DomainRoutingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()  # Remove port if present

        domain_mapping = {
            "omas.coffee": "omas.urls",
            "www.omas.coffee": "omas.urls",
        }

        if host in domain_mapping:
            request.urlconf = domain_mapping[host]

        response = self.get_response(request)
        return response
