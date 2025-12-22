from django.test import TestCase, override_settings


@override_settings(ROOT_URLCONF="omas.urls")
class OmasViewTests(TestCase):
    def test_home_view(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "omas/home.html")
        self.assertContains(response, "Omas Coffee")

    def test_home_view_content(self):
        response = self.client.get("/")
        self.assertContains(response, "Welcome to Omas Coffee")
        self.assertContains(response, "Premium Beans")
        self.assertContains(response, "Traditional Methods")
        self.assertContains(response, "Expert Craft")
        self.assertContains(response, "Cozy Atmosphere")


class DomainRoutingTests(TestCase):
    def test_omas_coffee_routing(self):
        response = self.client.get("/", headers={"host": "omas.coffee"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "omas/home.html")

    def test_www_omas_coffee_routing(self):
        response = self.client.get("/", headers={"host": "www.omas.coffee"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "omas/home.html")

    def test_main_site_routing(self):
        response = self.client.get("/", headers={"host": "aaronspindler.com"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateNotUsed(response, "omas/home.html")
