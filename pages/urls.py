from django.urls import path

from .views import home, render_blog_template

urlpatterns = [
    path("", home, name="home"),
    path("b/<str:template_name>/", render_blog_template, name="render_blog_template"),
]
