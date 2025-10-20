from django.contrib import admin
from django.contrib.sitemaps.views import index, sitemap
from django.urls import include, path
from django.views.decorators.cache import cache_page
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from .sitemaps import sitemaps

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Authentication
    path("accounts/", include("accounts.urls")),  # Custom accounts URLs (must be before allauth)
    path("accounts/", include("allauth.urls")),
    # API Documentation (OpenAPI/Swagger)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # API v1
    path("api/v1/", include("feefifofunds.api.urls")),
    # Sitemaps (cached for 12 hours)
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
    # App URLs
    path("photos/", include("photos.urls")),
    path("feefifofunds/", include("feefifofunds.urls")),
    path("", include("utils.urls")),
    path("", include("pages.urls")),
    path("", include("blog.urls")),
]
