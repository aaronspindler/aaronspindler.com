from django.urls import path
from django.contrib.sitemaps.views import sitemap

from pages.decorators import track_page_visit
from pages.sitemaps import BlogSitemap, StaticViewSitemap


from .views import home, render_blog_template, robotstxt

sitemaps = {
    "pages": StaticViewSitemap,
    "blog": BlogSitemap,
}

urlpatterns = [
    path("", track_page_visit(home), name="home"),
    path("sitemap.xml", track_page_visit(sitemap), {"sitemaps": sitemaps}),
    path("robots.txt", track_page_visit(robotstxt), name="robotstxt"),
    path("b/<str:template_name>/", track_page_visit(render_blog_template), name="render_blog_template"),
]
