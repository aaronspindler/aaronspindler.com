import os
from datetime import datetime

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.core.cache import cache
from django.urls import reverse

from photos.sitemaps import PhotoAlbumSitemap, PhotoSitemap


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""

    priority = 1.0
    changefreq = "monthly"
    protocol = "https"

    def items(self):
        return ["home", "lighthouse_history"]

    def location(self, item):
        return reverse(item)

    def lastmod(self, item):
        # Return current time for static pages
        return datetime.now()


class BlogPostSitemap(Sitemap):
    """Sitemap for blog posts"""

    # priority is defined as a method below
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        """Get all blog posts from template structure with caching"""
        cache_key = "sitemap_blog_posts_v1"
        blog_posts = cache.get(cache_key)

        if blog_posts is None:
            blog_posts = []
            template_dir = os.path.join(settings.BASE_DIR, "blog", "templates", "blog")

            # Define categories and their paths
            categories = {
                "personal": "personal",
                "projects": "projects",
                "reviews": "reviews",
                "tech": "tech",
            }

            for category, folder in categories.items():
                category_path = os.path.join(template_dir, folder)
                if os.path.exists(category_path):
                    for filename in os.listdir(category_path):
                        if filename.endswith(".html"):
                            # Remove the .html extension
                            template_name = filename[:-5]
                            blog_posts.append(
                                {
                                    "category": category,
                                    "template_name": template_name,
                                    "filename": filename,
                                }
                            )

            # Cache for 6 hours
            cache.set(cache_key, blog_posts, 21600)

        return blog_posts

    def location(self, item):
        """Generate URL for each blog post"""
        return f"/b/{item['category']}/{item['template_name']}/"

    def lastmod(self, item):
        """Get last modification time of the template file"""
        template_path = os.path.join(
            settings.BASE_DIR,
            "blog",
            "templates",
            "blog",
            item["category"],
            item["filename"],
        )
        if os.path.exists(template_path):
            timestamp = os.path.getmtime(template_path)
            return datetime.fromtimestamp(timestamp)
        return datetime.now()

    def priority(self, item):
        """Adjust priority based on blog post number (newer posts get higher priority)"""
        # Extract the number from the template name (e.g., 0005 from 0005_knowledge_graph)
        try:
            post_number = int(item["template_name"].split("_")[0])
            # Newer posts (higher numbers) get higher priority
            if post_number >= 5:
                return 0.9
            elif post_number >= 3:
                return 0.8
            else:
                return 0.7
        except (ValueError, IndexError):
            return 0.8


class DraftsSitemap(Sitemap):
    """Sitemap for draft pages (if you want them indexed)"""

    priority = 0.5
    changefreq = "monthly"
    protocol = "https"

    def items(self):
        """Get all draft pages from template structure"""
        draft_posts = []
        template_dir = os.path.join(settings.BASE_DIR, "blog", "templates", "drafts")

        if os.path.exists(template_dir):
            for root, dirs, files in os.walk(template_dir):
                for filename in files:
                    if filename.endswith(".html"):
                        # Get relative path from drafts directory
                        rel_dir = os.path.relpath(root, template_dir)
                        if rel_dir == ".":
                            category = ""
                        else:
                            category = rel_dir.replace(os.sep, "/")

                        template_name = filename[:-5]
                        draft_posts.append(
                            {
                                "category": category,
                                "template_name": template_name,
                                "filename": filename,
                            }
                        )

        return draft_posts

    def location(self, item):
        """Generate URL for each draft"""
        if item["category"]:
            return f"/d/{item['category']}/{item['template_name']}/"
        return f"/d/{item['template_name']}/"

    def lastmod(self, item):
        """Get last modification time of the template file"""
        if item["category"]:
            template_path = os.path.join(
                settings.BASE_DIR,
                "blog",
                "templates",
                "drafts",
                item["category"],
                item["filename"],
            )
        else:
            template_path = os.path.join(settings.BASE_DIR, "blog", "templates", "drafts", item["filename"])

        if os.path.exists(template_path):
            timestamp = os.path.getmtime(template_path)
            return datetime.fromtimestamp(timestamp)
        return datetime.now()


# Dictionary of all sitemaps
sitemaps = {
    "static": StaticViewSitemap,
    "blog": BlogPostSitemap,
    "photo_albums": PhotoAlbumSitemap,
    "photos": PhotoSitemap,
    # Uncomment if you want drafts included in sitemap
    # 'drafts': DraftsSitemap,
}
