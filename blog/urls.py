from django.urls import path

from .views import (
    delete_comment,
    knowledge_graph_api,
    knowledge_graph_screenshot,
    moderate_comment,
    render_blog_template,
    reply_to_comment,
    submit_comment,
    vote_comment,
)

urlpatterns = [
    path(
        "b/<str:category>/<str:template_name>/comment/",
        submit_comment,
        name="submit_comment",
    ),
    path("comment/<int:comment_id>/reply/", reply_to_comment, name="reply_to_comment"),
    path("comment/<int:comment_id>/moderate/", moderate_comment, name="moderate_comment"),
    path("comment/<int:comment_id>/delete/", delete_comment, name="delete_comment"),
    path("comment/<int:comment_id>/vote/", vote_comment, name="vote_comment"),
    # Knowledge graph API endpoints
    path("api/knowledge-graph/", knowledge_graph_api, name="knowledge_graph_api"),
    path(
        "api/knowledge-graph/screenshot/",
        knowledge_graph_screenshot,
        name="knowledge_graph_screenshot",
    ),
    # Blog post routes (category always required)
    path(
        "b/<str:category>/<str:template_name>/",
        render_blog_template,
        name="render_blog_template",
    ),
]
