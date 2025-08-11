from django.urls import path
from django.contrib.sitemaps.views import sitemap

from pages.decorators import track_page_visit
from pages.sitemaps import BlogSitemap, StaticViewSitemap


from .views import home, render_blog_template, robotstxt, knowledge_graph_page, knowledge_graph_api, clear_cache_endpoint

sitemaps = {
    "pages": StaticViewSitemap,
    "blog": BlogSitemap,
}

urlpatterns = [
    path("", track_page_visit(home), name="home"),
    path("sitemap.xml", track_page_visit(sitemap), {"sitemaps": sitemaps}),
    path("robots.txt", track_page_visit(robotstxt), name="robotstxt"),
    path("b/<str:template_name>/", track_page_visit(render_blog_template), name="render_blog_template"),
    path("knowledge-graph/", track_page_visit(knowledge_graph_page), name="knowledge_graph_page"),
    path("api/knowledge-graph/", knowledge_graph_api, name="knowledge_graph_api"),
    path("api/clear-cache/", clear_cache_endpoint, name="clear_cache_endpoint"),
]
