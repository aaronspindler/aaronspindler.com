from django.urls import reverse
from config.testcases import BaseTestCase


class PageViewTests(BaseTestCase):
    def test_home_view_unpaid_user(self):
        self.client.force_login(self.unpaid_user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/unpaid_home.html")
    
    def test_home_view_unauthenticated(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/landing_page.html")

    def test_home_view_paid_user(self):
        self.client.force_login(self.paid_user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/paid_home.html")