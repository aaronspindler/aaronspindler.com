from django.test import TestCase, RequestFactory
from utils.models import LighthouseAudit
from utils.context_processors import lighthouse_badge


class LighthouseBadgeContextProcessorTests(TestCase):
    """Test cases for the lighthouse badge context processor."""

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')

    def test_no_audits_exist(self):
        """Test context processor returns False when no audits exist."""
        context = lighthouse_badge(self.request)
        self.assertFalse(context['show_lighthouse_badge'])

    def test_audits_exist(self):
        """Test context processor returns True when audits exist."""
        LighthouseAudit.objects.create(
            url='https://example.com',
            performance_score=95,
            accessibility_score=90,
            best_practices_score=85,
            seo_score=100,
            pwa_score=80,
        )
        context = lighthouse_badge(self.request)
        self.assertTrue(context['show_lighthouse_badge'])

