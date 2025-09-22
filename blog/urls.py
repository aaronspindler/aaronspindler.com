from django.urls import path

from pages.decorators import track_page_visit

from .views import (
    render_blog_template, 
    knowledge_graph_api, 
    knowledge_graph_screenshot,
    submit_comment,
    reply_to_comment,
    moderate_comment,
    delete_comment
)

urlpatterns = [
    # Blog routes
    path("b/<str:category>/<str:template_name>/", track_page_visit(render_blog_template), name="render_blog_template_with_category"),
    path("b/<str:template_name>/", track_page_visit(render_blog_template), name="render_blog_template"),
    
    # Comment routes
    path("b/<str:category>/<str:template_name>/comment/", submit_comment, name="submit_comment_with_category"),
    path("b/<str:template_name>/comment/", submit_comment, name="submit_comment"),
    path("comment/<int:comment_id>/reply/", reply_to_comment, name="reply_to_comment"),
    path("comment/<int:comment_id>/moderate/", moderate_comment, name="moderate_comment"),
    path("comment/<int:comment_id>/delete/", delete_comment, name="delete_comment"),
    
    # Knowledge graph API routes
    path("api/knowledge-graph/", knowledge_graph_api, name="knowledge_graph_api"),
    path("api/knowledge-graph/screenshot/", knowledge_graph_screenshot, name="knowledge_graph_screenshot"),
]
