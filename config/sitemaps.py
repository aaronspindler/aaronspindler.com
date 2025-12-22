import os
from datetime import datetime

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.core.cache import cache
from django.urls import reverse

from photos.sitemaps import PhotoAlbumSitemap, PhotoSitemap


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "monthly"
    protocol = "https"

    def items(self):
        return ["home", "lighthouse_history"]

    def location(self, item):
        return reverse(item)

    def lastmod(self, item):
        return datetime.now()


class BlogPostSitemap(Sitemap):
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        cache_key = "sitemap_blog_posts_v1"
        blog_posts = cache.get(cache_key)

        if blog_posts is None:
            blog_posts = []
            template_dir = os.path.join(settings.BASE_DIR, "blog", "templates", "blog")

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
                            template_name = filename[:-5]
                            blog_posts.append(
                                {
                                    "category": category,
                                    "template_name": template_name,
                                    "filename": filename,
                                }
                            )

            cache.set(cache_key, blog_posts, 21600)

        return blog_posts

    def location(self, item):
        return f"/b/{item['category']}/{item['template_name']}/"

    def lastmod(self, item):
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
        try:
            post_number = int(item["template_name"].split("_")[0])
            if post_number >= 5:
                return 0.9
            elif post_number >= 3:
                return 0.8
            else:
                return 0.7
        except (ValueError, IndexError):
            return 0.8


class DraftsSitemap(Sitemap):
    priority = 0.5
    changefreq = "monthly"
    protocol = "https"

    def items(self):
        draft_posts = []
        template_dir = os.path.join(settings.BASE_DIR, "blog", "templates", "drafts")

        if os.path.exists(template_dir):
            for root, _dirs, files in os.walk(template_dir):
                for filename in files:
                    if filename.endswith(".html"):
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
        if item["category"]:
            return f"/d/{item['category']}/{item['template_name']}/"
        return f"/d/{item['template_name']}/"

    def lastmod(self, item):
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


sitemaps = {
    "static": StaticViewSitemap,
    "blog": BlogPostSitemap,
    "photo_albums": PhotoAlbumSitemap,
    "photos": PhotoSitemap,
}
