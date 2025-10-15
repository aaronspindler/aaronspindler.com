from django.contrib import admin
from django.contrib.sitemaps.views import index, sitemap
from django.urls import include, path
from django.views.decorators.cache import cache_page

from .sitemaps import sitemaps

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),  # Custom accounts URLs (must be before allauth)
    path("accounts/", include("allauth.urls")),
    # Cache sitemap views for 12 hours (43200 seconds)
    path(
        "sitemap.xml",
        cache_page(43200)(index),
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.index",
    ),
    path(
        "sitemap-<section>.xml",
        cache_page(43200)(sitemap),
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("photos/", include("photos.urls")),
    path("", include("utils.urls")),
    path("", include("pages.urls")),
    path("", include("blog.urls")),
]
