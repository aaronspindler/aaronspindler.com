from django.contrib.sites.models import Site
from django.test import Client, TestCase, LiveServerTestCase
from django.urls import reverse
from accounts.models import CustomUser
from actions.models import Action
from utils.models import HTTPStatusCode
from web.models import Endpoint

class BaseTestCase(TestCase):
    databases = "__all__"
    
    def get_full_url_from_name(self, name):
        return self.live_server_url + reverse(name)
    
    def create_endpoint(self, status_code, url_name, http_method="GET", check_ssl=False, check_domain_expiration=False, follow_redirects=True, **kwargs):
        status = HTTPStatusCode.objects.get(code=status_code)
        endpoint = Endpoint.objects.create(
            owner=self.paid_user,
            url=self.get_full_url_from_name(url_name),
            http_method=http_method,
            check_ssl=check_ssl,
            check_domain_expiration=check_domain_expiration,
            follow_redirects=follow_redirects,
            **kwargs
        )
        endpoint.up_status_codes.add(status)
        return endpoint

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.site = Site.objects.create(domain="testserver", name="testserver")
        self.paid_user = CustomUser.objects.create_user(email="testuser@example.com", username="testuser", password="testpassword", paid=True)
        self.other_user = CustomUser.objects.create_user(email="testuser2@example.com", username="testuser2", password="testpassword2", paid=True)
        self.unpaid_user = CustomUser.objects.create_user(email="testuser3@example.com", username="testuser3", password="testpassword3", paid=False)
        
        self.failure_action = Action.objects.create(owner=self.paid_user, url='https://github.com/aaronspindler/actions_uptime_demo/actions/workflows/action_failure.yml')
        self.success_action = Action.objects.create(owner=self.paid_user, url='https://github.com/aaronspindler/actions_uptime_demo/actions/workflows/action_success.yml')
        
        self.http_200, _ = HTTPStatusCode.objects.get_or_create(code=200, description="OK")
        self.http_404, _ = HTTPStatusCode.objects.get_or_create(code=404, description="Not Found")
        self.http_500, _ = HTTPStatusCode.objects.get_or_create(code=500, description="Internal Server Error")
        self.http_503, _ = HTTPStatusCode.objects.get_or_create(code=503, description="Service Unavailable")
        self.http_301, _ = HTTPStatusCode.objects.get_or_create(code=301, description="Moved Permanently")
        self.http_302, _ = HTTPStatusCode.objects.get_or_create(code=302, description="Found")

    def get_admin_subscription_metadata(self):
        return {
            "private_actions": True,
            "sms_notifications": True,
            "action_types": ["public", "private"],
            "num_monitors": -1,
            "monitor_interval": "15S",
            "notification_types": ["email", "sms"],
            "endpoint_regions": ["CA", "US", "EU", "AP", "AF", "SA", "ME"],
        }

class BaseLiveTestCase(LiveServerTestCase, BaseTestCase):
    pass