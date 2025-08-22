from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
import os
from django.conf import settings
from django.contrib.sites.models import Site

from pages.utils import get_blog_from_template_name, get_all_blog_posts

class BaseSitemap(Sitemap):
    """Base sitemap class with proper domain handling."""
    
    def get_urls(self, page=1, site=None, protocol=None):
        """Override to use the correct domain."""
        # Try to get the correct domain from settings or Site model
        if site is None:
            try:
                site = Site.objects.get_current()
                # If we're in development and site is still example.com, use localhost
                if site.domain == 'example.com' and settings.DEBUG:
                    site.domain = 'localhost:8000'
                # In production, use the first allowed host that's not localhost
                elif site.domain == 'example.com' and not settings.DEBUG:
                    for host in settings.ALLOWED_HOSTS:
                        if host not in ['localhost', '127.0.0.1']:
                            site.domain = host
                            break
            except Site.DoesNotExist:
                # Fallback to first non-localhost allowed host
                for host in settings.ALLOWED_HOSTS:
                    if host not in ['localhost', '127.0.0.1']:
                        site = type('obj', (object,), {'domain': host})
                        break
        
        # Use https in production, http in development
        if protocol is None:
            protocol = 'http' if settings.DEBUG else 'https'
            
        return super().get_urls(page=page, site=site, protocol=protocol)

class StaticViewSitemap(BaseSitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return ['home']

    def location(self, item):
        return reverse(item)

class BlogSitemap(BaseSitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        # Get all blog posts from all categories
        return get_all_blog_posts()

    def location(self, item):
        # Generate the appropriate URL based on whether the post has a category
        if item.get('category'):
            return reverse('render_blog_template_with_category', 
                          args=[item['category'], item['template_name']])
        else:
            return reverse('render_blog_template', args=[item['template_name']])

    def lastmod(self, item):
        # Get the file modification time as a fallback for lastmod
        try:
            file_path = item.get('full_path')
            if file_path and os.path.exists(file_path):
                timestamp = os.path.getmtime(file_path)
                return timezone.datetime.fromtimestamp(timestamp, tz=timezone.get_current_timezone())
        except Exception:
            pass
        # Return None if we can't determine the last modification time
        return None