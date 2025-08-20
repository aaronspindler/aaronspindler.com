from django.urls import path
from django.contrib.sitemaps.views import sitemap

from pages.decorators import track_page_visit
from pages.sitemaps import BlogSitemap, StaticViewSitemap


from .views import home, render_blog_template, robotstxt, knowledge_graph_api, knowledge_graph_screenshot

sitemaps = {
    "pages": StaticViewSitemap,
    "blog": BlogSitemap,
}

urlpatterns = [
    path("", track_page_visit(home), name="home"),
    path("sitemap.xml", track_page_visit(sitemap), {"sitemaps": sitemaps}),
    path("robots.txt", track_page_visit(robotstxt), name="robotstxt"),
    # Support both category-based and direct blog URLs
    path("b/<str:category>/<str:template_name>/", track_page_visit(render_blog_template), name="render_blog_template_with_category"),
    path("b/<str:template_name>/", track_page_visit(render_blog_template), name="render_blog_template"),
    path("api/knowledge-graph/", knowledge_graph_api, name="knowledge_graph_api"),
    path("api/knowledge-graph/screenshot/", knowledge_graph_screenshot, name="knowledge_graph_screenshot"),
]
