from django.test import TestCase, Client
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, MagicMock
from pages.models import PageVisit
from pages.admin import PageVisitAdmin
from tests.factories import PageVisitFactory, UserFactory
import json

User = get_user_model()


class PageVisitAdminTest(TestCase):
    """Test PageVisit admin interface."""
    
    def setUp(self):
        self.site = AdminSite()
        self.admin = PageVisitAdmin(PageVisit, self.site)
        self.superuser = UserFactory.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.client = Client()
        
    def test_list_display_fields(self):
        """Test that list display shows correct fields."""
        expected_fields = ['page_name', 'ip_address', 'created_at', 'geo_data']
        self.assertEqual(self.admin.list_display, expected_fields)
        
    def test_list_filter_fields(self):
        """Test that list filter has correct fields."""
        expected_filters = ('page_name', 'created_at', 'ip_address')
        self.assertEqual(self.admin.list_filter, expected_filters)
        
    def test_search_fields(self):
        """Test searchable fields."""
        expected_search = ('page_name', 'ip_address', 'geo_data')
        self.assertEqual(self.admin.search_fields, expected_search)
        
    def test_readonly_fields(self):
        """Test that certain fields are read-only."""
        readonly = ('created_at', 'ip_address', 'page_name', 'geo_data')
        self.assertEqual(self.admin.readonly_fields, readonly)
        
    def test_date_hierarchy(self):
        """Test date hierarchy is set."""
        self.assertEqual(self.admin.date_hierarchy, 'created_at')
        
    def test_ordering(self):
        """Test default ordering."""
        self.assertEqual(self.admin.ordering, ('-created_at',))
        
    @patch('pages.admin.requests.post')
    def test_geolocate_ips_action(self, mock_post):
        """Test batch geolocation action."""
        # Create test visits without geo data
        PageVisitFactory.create_visit(ip_address='8.8.8.8', page_name='/test1/')
        PageVisitFactory.create_visit(ip_address='8.8.4.4', page_name='/test2/')
        PageVisitFactory.create_visit(ip_address='127.0.0.1', page_name='/local/')  # Local IP
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'status': 'success',
                'query': '8.8.8.8',
                'country': 'United States',
                'city': 'Mountain View'
            },
            {
                'status': 'success',
                'query': '8.8.4.4',
                'country': 'United States',
                'city': 'Mountain View'
            }
        ]
        mock_post.return_value = mock_response
        
        self.client.login(username='admin', password='admin123')
        
        # Call the admin action
        request = MagicMock()
        request.user = self.superuser
        
        self.admin.geolocate_ips(request)
        
        # Check that geo data was updated
        visit1 = PageVisit.objects.get(ip_address='8.8.8.8')
        self.assertIsNotNone(visit1.geo_data)
        self.assertEqual(visit1.geo_data['country'], 'United States')
        
        # Local IP should not have geo data
        local_visit = PageVisit.objects.get(ip_address='127.0.0.1')
        self.assertIsNone(local_visit.geo_data)
        
    @patch('pages.admin.requests.post')
    def test_geolocate_ips_handles_api_error(self, mock_post):
        """Test that geolocation handles API errors gracefully."""
        PageVisitFactory.create_visit(ip_address='8.8.8.8', page_name='/test/')
        
        mock_post.side_effect = Exception('API error')
        
        request = MagicMock()
        request.user = self.superuser
        
        # Should not raise exception
        result = self.admin.geolocate_ips(request)
        
        # Should redirect
        self.assertEqual(result.status_code, 302)
        
    def test_clean_local_ips_action(self):
        """Test cleaning local IP addresses."""
        # Create visits with various IPs
        PageVisitFactory.create_visit(ip_address='192.168.1.1', page_name='/test1/')
        PageVisitFactory.create_visit(ip_address='127.0.0.1', page_name='/local1/')
        PageVisitFactory.create_visit(ip_address='10.0.2.2', page_name='/local2/')
        PageVisitFactory.create_visit(ip_address='10.0.1.5', page_name='/local3/')
        PageVisitFactory.create_visit(ip_address='8.8.8.8', page_name='/public/')
        
        request = MagicMock()
        request.user = self.superuser
        
        self.admin.clean_local_ips(request)
        
        # Check that local IPs were removed
        remaining_visits = PageVisit.objects.all()
        self.assertEqual(remaining_visits.count(), 2)
        
        # Public and non-local IPs should remain
        self.assertTrue(PageVisit.objects.filter(ip_address='192.168.1.1').exists())
        self.assertTrue(PageVisit.objects.filter(ip_address='8.8.8.8').exists())
        
        # Local IPs should be gone
        self.assertFalse(PageVisit.objects.filter(ip_address='127.0.0.1').exists())
        self.assertFalse(PageVisit.objects.filter(ip_address='10.0.2.2').exists())
        
    @patch('pages.admin.requests.post')
    def test_geolocate_ips_batch_processing(self, mock_post):
        """Test that IPs are processed in batches of 100."""
        # Create 150 visits (should be 2 batches)
        for i in range(150):
            PageVisitFactory.create_visit(
                ip_address=f'1.2.3.{i % 256}',
                page_name=f'/test{i}/'
            )
        
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_post.return_value = mock_response
        
        request = MagicMock()
        request.user = self.superuser
        
        self.admin.geolocate_ips(request)
        
        # Should make 2 API calls (100 + 50)
        self.assertEqual(mock_post.call_count, 2)
        
    def test_custom_admin_urls(self):
        """Test that custom admin URLs are registered."""
        urls = self.admin.get_urls()
        
        url_names = [url.name for url in urls]
        self.assertIn('pages_pagevisit_geolocate_ips', url_names)
        self.assertIn('pages_pagevisit_clean_local_ips', url_names)
        
    @patch('pages.admin.requests.post')
    def test_geolocate_ips_filters_existing_geodata(self, mock_post):
        """Test that geolocation skips IPs that already have geo data."""
        # Create visits with and without geo data
        PageVisitFactory.create_visit(
            ip_address='8.8.8.8',
            page_name='/test1/',
            geo_data={'country': 'Existing'}
        )
        PageVisitFactory.create_visit(
            ip_address='8.8.4.4',
            page_name='/test2/',
            geo_data=None
        )
        
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'status': 'success',
                'query': '8.8.4.4',
                'country': 'United States'
            }
        ]
        mock_post.return_value = mock_response
        
        request = MagicMock()
        request.user = self.superuser
        
        self.admin.geolocate_ips(request)
        
        # Should only process the IP without geo data
        call_args = mock_post.call_args[0][0]
        ips_sent = json.loads(call_args)
        self.assertEqual(ips_sent, ['8.8.4.4'])
        
    @patch('pages.admin.requests.post')
    def test_geolocate_ips_handles_failed_status(self, mock_post):
        """Test handling of failed geolocation status."""
        PageVisitFactory.create_visit(ip_address='192.168.1.1', page_name='/test/')
        
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'status': 'fail',
                'query': '192.168.1.1',
                'message': 'private range'
            }
        ]
        mock_post.return_value = mock_response
        
        request = MagicMock()
        request.user = self.superuser
        
        self.admin.geolocate_ips(request)
        
        # Geo data should not be updated for failed status
        visit = PageVisit.objects.get(ip_address='192.168.1.1')
        self.assertIsNone(visit.geo_data)
