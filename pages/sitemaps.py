from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
import os
from django.conf import settings

from pages.utils import get_blog_from_template_name

class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return ['home']

    def location(self, item):
        return reverse(item)

class BlogSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        blog_templates_path = os.path.join(settings.BASE_DIR, 'templates', 'blog')
        return [template.split('.')[0] for template in os.listdir(blog_templates_path) if template.endswith('.html')]

    def location(self, item):
        return reverse('render_blog_template', args=[item])

    def lastmod(self, item):
        blog_data = get_blog_from_template_name(item)
        return timezone.datetime.fromtimestamp(blog_data['updated_timestamp'])