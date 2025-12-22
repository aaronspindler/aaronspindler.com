from django.test import RequestFactory, TestCase

from utils.context_processors import lighthouse_badge
from utils.models import LighthouseAudit


class LighthouseBadgeContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/")

    def test_no_audits_exist(self):
        context = lighthouse_badge(self.request)
        self.assertFalse(context["show_lighthouse_badge"])

    def test_audits_exist(self):
        LighthouseAudit.objects.create(
            url="https://example.com",
            performance_score=95,
            accessibility_score=90,
            best_practices_score=85,
            seo_score=100,
        )
        context = lighthouse_badge(self.request)
        self.assertTrue(context["show_lighthouse_badge"])
