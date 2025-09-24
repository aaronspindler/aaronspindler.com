from django.test import TestCase
from django.utils import timezone
from pages.models import PageVisit
from datetime import datetime


class PageVisitModelTest(TestCase):
    """Test PageVisit model functionality."""

    def test_page_visit_creation(self):
        """Test creating a page visit record."""
        visit = PageVisit.objects.create(
            ip_address='192.168.1.1',
            page_name='/test-page/'
        )
        
        self.assertEqual(visit.ip_address, '192.168.1.1')
        self.assertEqual(visit.page_name, '/test-page/')
        self.assertIsNotNone(visit.created_at)
        self.assertIsNone(visit.geo_data)
        
    def test_page_visit_with_geo_data(self):
        """Test creating a page visit with geolocation data."""
        geo_data = {
            'country': 'United States',
            'city': 'New York',
            'lat': 40.7128,
            'lon': -74.0060
        }
        
        visit = PageVisit.objects.create(
            ip_address='8.8.8.8',
            page_name='/blog/',
            geo_data=geo_data
        )
        
        self.assertEqual(visit.geo_data['country'], 'United States')
        self.assertEqual(visit.geo_data['city'], 'New York')
        
    def test_page_visit_str_representation(self):
        """Test the string representation of PageVisit."""
        now = timezone.now()
        visit = PageVisit.objects.create(
            ip_address='10.0.0.1',
            page_name='/about/',
            created_at=now
        )
        
        expected_str = f"/about/ visited from 10.0.0.1 at {now}"
        self.assertEqual(str(visit), expected_str)
        
    def test_page_visit_ordering(self):
        """Test that page visits are ordered by creation time."""
        visit1 = PageVisit.objects.create(
            ip_address='192.168.1.1',
            page_name='/page1/'
        )
        
        visit2 = PageVisit.objects.create(
            ip_address='192.168.1.2',
            page_name='/page2/'
        )
        
        visits = PageVisit.objects.all()
        self.assertEqual(visits[0], visit1)
        self.assertEqual(visits[1], visit2)
        
    def test_page_visit_ipv6_support(self):
        """Test that IPv6 addresses are supported."""
        visit = PageVisit.objects.create(
            ip_address='2001:0db8:85a3:0000:0000:8a2e:0370:7334',
            page_name='/test/'
        )
        
        self.assertEqual(visit.ip_address, '2001:0db8:85a3:0000:0000:8a2e:0370:7334')
        
    def test_page_visit_long_page_names(self):
        """Test handling of long page names."""
        long_page_name = '/very/long/path/' + 'x' * 200 + '/'
        
        visit = PageVisit.objects.create(
            ip_address='192.168.1.1',
            page_name=long_page_name[:255]  # Truncate to max length
        )
        
        self.assertEqual(len(visit.page_name), 255)
        
    def test_page_visit_bulk_create(self):
        """Test bulk creating page visits for performance."""
        visits_data = [
            PageVisit(ip_address=f'192.168.1.{i}', page_name=f'/page{i}/')
            for i in range(100)
        ]
        
        PageVisit.objects.bulk_create(visits_data)
        
        self.assertEqual(PageVisit.objects.count(), 100)
        
    def test_page_visit_filtering_by_ip(self):
        """Test filtering visits by IP address."""
        PageVisit.objects.create(ip_address='192.168.1.1', page_name='/page1/')
        PageVisit.objects.create(ip_address='192.168.1.1', page_name='/page2/')
        PageVisit.objects.create(ip_address='192.168.1.2', page_name='/page3/')
        
        visits_from_ip = PageVisit.objects.filter(ip_address='192.168.1.1')
        self.assertEqual(visits_from_ip.count(), 2)
        
    def test_page_visit_filtering_by_page(self):
        """Test filtering visits by page name."""
        PageVisit.objects.create(ip_address='192.168.1.1', page_name='/blog/')
        PageVisit.objects.create(ip_address='192.168.1.2', page_name='/blog/')
        PageVisit.objects.create(ip_address='192.168.1.3', page_name='/about/')
        
        blog_visits = PageVisit.objects.filter(page_name='/blog/')
        self.assertEqual(blog_visits.count(), 2)
        
    def test_page_visit_date_filtering(self):
        """Test filtering visits by date range."""
        from datetime import timedelta
        
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        
        PageVisit.objects.create(
            ip_address='192.168.1.1',
            page_name='/old/',
            created_at=yesterday
        )
        PageVisit.objects.create(
            ip_address='192.168.1.2',
            page_name='/today/'
        )
        
        recent_visits = PageVisit.objects.filter(created_at__gte=now - timedelta(hours=1))
        self.assertEqual(recent_visits.count(), 1)
        self.assertEqual(recent_visits.first().page_name, '/today/')
