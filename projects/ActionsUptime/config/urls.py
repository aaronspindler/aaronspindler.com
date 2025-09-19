from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap

from config.sitemaps import StaticViewSitemap
from utils.views import robotstxt
sitemaps = {
    "pages": StaticViewSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}),
    path("robots.txt", robotstxt, name="robotstxt"),
    path("accounts/", include("allauth.urls")),
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    path("actions/", include("actions.urls")),
    path("web/", include("web.urls")),
    path("", include("pages.urls")),
    path("", include("utils.urls")),
]

if settings.DEBUG:
     import debug_toolbar

     urlpatterns = [
         path("__debug__/", include(debug_toolbar.urls)),
     ] + urlpatterns
