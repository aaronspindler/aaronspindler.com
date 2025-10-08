from django.test import TestCase
from lighthouse_monitor.models import LighthouseAudit


class LighthouseAuditModelTests(TestCase):
    """Test cases for the LighthouseAudit model."""

    def test_create_audit(self):
        """Test creating a basic Lighthouse audit."""
        audit = LighthouseAudit.objects.create(
            url='https://example.com',
            performance_score=95,
            accessibility_score=90,
            best_practices_score=85,
            seo_score=100,
        )
        self.assertEqual(audit.url, 'https://example.com')
        self.assertEqual(audit.performance_score, 95)

    def test_average_score_calculation(self):
        """Test that average_score property calculates correctly."""
        audit = LighthouseAudit.objects.create(
            url='https://example.com',
            performance_score=100,
            accessibility_score=90,
            best_practices_score=80,
            seo_score=70,
        )
        expected_average = (100 + 90 + 80 + 70) / 4
        self.assertEqual(audit.average_score, round(expected_average))

    def test_color_class_success(self):
        """Test color_class returns 'success' for high scores."""
        audit = LighthouseAudit.objects.create(
            url='https://example.com',
            performance_score=95,
            accessibility_score=95,
            best_practices_score=95,
            seo_score=95,
        )
        self.assertEqual(audit.color_class, 'success')

    def test_color_class_warning(self):
        """Test color_class returns 'warning' for medium scores."""
        audit = LighthouseAudit.objects.create(
            url='https://example.com',
            performance_score=80,
            accessibility_score=80,
            best_practices_score=80,
            seo_score=80,
        )
        self.assertEqual(audit.color_class, 'warning')

    def test_color_class_danger(self):
        """Test color_class returns 'danger' for low scores."""
        audit = LighthouseAudit.objects.create(
            url='https://example.com',
            performance_score=60,
            accessibility_score=60,
            best_practices_score=60,
            seo_score=60,
        )
        self.assertEqual(audit.color_class, 'danger')

    def test_string_representation(self):
        """Test the string representation of a LighthouseAudit."""
        audit = LighthouseAudit.objects.create(
            url='https://example.com',
            performance_score=95,
            accessibility_score=90,
            best_practices_score=85,
            seo_score=100,
        )
        self.assertIn('https://example.com', str(audit))
        self.assertIn('Audit for', str(audit))

