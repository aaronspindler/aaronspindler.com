from django.urls import path

from pages.decorators import track_page_visit

from .views import render_blog_template, knowledge_graph_api, knowledge_graph_screenshot

urlpatterns = [
    # Blog routes
    path("b/<str:category>/<str:template_name>/", track_page_visit(render_blog_template), name="render_blog_template_with_category"),
    path("b/<str:template_name>/", track_page_visit(render_blog_template), name="render_blog_template"),
    
    # Knowledge graph API routes
    path("api/knowledge-graph/", knowledge_graph_api, name="knowledge_graph_api"),
    path("api/knowledge-graph/screenshot/", knowledge_graph_screenshot, name="knowledge_graph_screenshot"),
]
