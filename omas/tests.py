from django.test import TestCase, override_settings


@override_settings(ROOT_URLCONF="omas.urls")
class OmasViewTests(TestCase):
    """Test cases for Omas Coffee views."""

    def test_home_view(self):
        """Test that the home page loads successfully."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "omas/home.html")
        self.assertContains(response, "Omas Coffee")

    def test_home_view_content(self):
        """Test that the home page contains expected content."""
        response = self.client.get("/")
        self.assertContains(response, "Welcome to Omas Coffee")
        self.assertContains(response, "Premium Beans")
        self.assertContains(response, "Traditional Methods")
        self.assertContains(response, "Expert Craft")
        self.assertContains(response, "Cozy Atmosphere")


class DomainRoutingTests(TestCase):
    """Test cases for domain-based routing."""

    def test_omas_coffee_routing(self):
        """Test that omas.coffee domain routes to omas.urls."""
        response = self.client.get("/", headers={"host": "omas.coffee"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "omas/home.html")

    def test_www_omas_coffee_routing(self):
        """Test that www.omas.coffee domain routes to omas.urls."""
        response = self.client.get("/", headers={"host": "www.omas.coffee"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "omas/home.html")

    def test_main_site_routing(self):
        """Test that the main site (aaronspindler.com) uses default routing."""
        response = self.client.get("/", headers={"host": "aaronspindler.com"})
        self.assertEqual(response.status_code, 200)
        # Should use the main site's home page, not omas
        self.assertTemplateNotUsed(response, "omas/home.html")
