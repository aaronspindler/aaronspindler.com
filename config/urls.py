from django.contrib import admin
from django.contrib.sitemaps.views import sitemap, index
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .sitemaps import sitemaps

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("sitemap.xml", index, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.index"),
    path("sitemap-<section>.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("", include("pages.urls")),
    path("", include("blog.urls")),
]

# Serve media files in development (when not using S3)
if settings.DEBUG and not settings.USE_S3:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)