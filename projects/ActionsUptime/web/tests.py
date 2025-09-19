from config.testcases import BaseLiveTestCase, BaseTestCase
from web.models import EndpointStatus
from web.tasks import check_endpoint_status_local


class EndpointTaskTests(BaseLiveTestCase):
    def test_check_endpoint_status_local_get_success(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view__get_success")
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "success")
        self.assertEqual(EndpointStatus.objects.last().status_code, 200)
    
    def test_check_endpoint_status_local_get_failure(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view__get_failure")
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "failure")
        self.assertEqual(EndpointStatus.objects.last().status_code, 404)
        
    def test_check_endpoint_status_local_post_success(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view__post_success", http_method="POST")
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "success")
        self.assertEqual(EndpointStatus.objects.last().status_code, 200)
        
    def test_check_endpoint_status_local_post_failure(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view__post_failure", http_method="POST")
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "failure")
        self.assertEqual(EndpointStatus.objects.last().status_code, 404)
        
    def test_check_endpoint_status_local_post_json_success(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view__post_json_success", http_method="POST", send_body_as_json=True, request_body='{"test": "test"}')
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "success")
        self.assertEqual(EndpointStatus.objects.last().status_code, 200)
        
    def test_check_endpoint_status_local_post_body_success(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view__post_body_success", http_method="POST", request_body='{"test": "test"}')
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "success")
        self.assertEqual(EndpointStatus.objects.last().status_code, 200)
    
    def test_check_endpoint_status_local_redirect_get_success(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view_redirect_get")
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "success")
        self.assertEqual(EndpointStatus.objects.last().status_code, 200)
    
    def test_check_endpoint_status_local_redirect_get_dont_follow_redirects(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view_redirect_get", follow_redirects=False)
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "failure")
        self.assertEqual(EndpointStatus.objects.last().status_code, 302)
    
    def test_check_endpoint_status_local_slow_response(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view__slow_response", request_timeout_seconds=1)
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "failure")
        self.assertEqual(EndpointStatus.objects.last().status_code, 504)
    
    def test_check_endpoint_status_local_custom_header(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view__custom_header", request_headers='{"X-Custom-Header": "Test Value"}')
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "success")
        self.assertEqual(EndpointStatus.objects.last().status_code, 200)
        
    def test_check_endpoint_status_local_multiple_custom_header(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view__custom_header", request_headers='{"X-Custom-Header": "Test Value", "X-Custom-Header-2": "Test Value 2"}')
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "success")
        self.assertEqual(EndpointStatus.objects.last().status_code, 200)
        
    def test_check_endpoint_status_local_custom_header_missing(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view__custom_header")
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "failure")
        self.assertEqual(EndpointStatus.objects.last().status_code, 404)
    
    def test_check_endpoint_status_local_server_error(self):
        pre_count = EndpointStatus.objects.count()
        endpoint = self.create_endpoint(200, "testing_view__server_error")
        check_endpoint_status_local(endpoint.id)
        self.assertEqual(EndpointStatus.objects.count(), pre_count + 1)
        self.assertEqual(EndpointStatus.objects.last().status, "failure")
        self.assertEqual(EndpointStatus.objects.last().status_code, 500)

class EndpointModelTests(BaseTestCase):
    pass
        
class EndpointFormTests(BaseTestCase):
    pass