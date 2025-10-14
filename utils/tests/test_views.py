from django.test import TestCase
from django.urls import reverse

from utils.models import LighthouseAudit


class BadgeEndpointTests(TestCase):
    """Test cases for the badge endpoint."""

    def test_badge_endpoint_no_data(self):
        """Test badge endpoint returns 404 when no audits exist."""
        response = self.client.get(reverse("lighthouse_badge"))
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["message"], "no data")
        self.assertEqual(data["color"], "lightgrey")

    def test_badge_endpoint_with_data(self):
        """Test badge endpoint returns correct data when audits exist."""
        LighthouseAudit.objects.create(
            url="https://example.com",
            performance_score=95,
            accessibility_score=90,
            best_practices_score=85,
            seo_score=100,
        )
        response = self.client.get(reverse("lighthouse_badge"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["schemaVersion"], 1)
        self.assertEqual(data["label"], "lighthouse")
        self.assertEqual(data["message"], "95/90/85/100")
        self.assertEqual(data["color"], "brightgreen")

    def test_badge_color_yellow_for_medium_scores(self):
        """Test badge endpoint returns yellow color for medium scores."""
        LighthouseAudit.objects.create(
            url="https://example.com",
            performance_score=80,
            accessibility_score=80,
            best_practices_score=80,
            seo_score=80,
        )
        response = self.client.get(reverse("lighthouse_badge"))
        data = response.json()
        self.assertEqual(data["color"], "yellow")

    def test_badge_color_red_for_low_scores(self):
        """Test badge endpoint returns red color for low scores."""
        LighthouseAudit.objects.create(
            url="https://example.com",
            performance_score=60,
            accessibility_score=60,
            best_practices_score=60,
            seo_score=60,
        )
        response = self.client.get(reverse("lighthouse_badge"))
        data = response.json()
        self.assertEqual(data["color"], "red")


class HistoryPageTests(TestCase):
    """Test cases for the history page."""

    def test_history_page_loads(self):
        """Test that the history page loads successfully."""
        response = self.client.get(reverse("lighthouse_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lighthouse Performance History")

    def test_history_page_no_audits(self):
        """Test history page displays appropriate message when no audits exist."""
        response = self.client.get(reverse("lighthouse_history"))
        self.assertContains(response, "No Lighthouse audits have been run yet")

    def test_history_page_with_audits(self):
        """Test history page displays audit data correctly."""
        audit = LighthouseAudit.objects.create(
            url="https://example.com",
            performance_score=95,
            accessibility_score=90,
            best_practices_score=85,
            seo_score=100,
        )
        response = self.client.get(reverse("lighthouse_history"))
        self.assertContains(response, "Latest Audit")
        self.assertContains(response, "95")
        self.assertContains(response, "90")
        self.assertContains(response, "Performance Trend")
