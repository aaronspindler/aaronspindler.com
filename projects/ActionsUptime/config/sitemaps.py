from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    def items(self):
        return ['home', 'privacy-policy', 'terms-of-service', 'support', 'roadmap']

    def location(self, item):
        return reverse(item)