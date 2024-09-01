from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.shortcuts import render

from pages.utils import get_blog_from_template_name

import os
from django.conf import settings

def home(request):
    blog_posts = []
    blog_templates_path = os.path.join(settings.BASE_DIR, 'templates', 'blog')
    for template_name in os.listdir(blog_templates_path):
        if template_name.endswith('.html'):
            template_name = template_name.split('.')[0]
            blog_posts.append(get_blog_from_template_name(template_name))
    blog_posts.sort(key=lambda x: x['created_timestamp'], reverse=True)
    return render(request, "pages/home.html", {"blog_posts": blog_posts})


def render_blog_template(request, template_name):
    try:
        blog_data = get_blog_from_template_name(template_name)
        return render(request, "_blog_base.html", blog_data)
    except TemplateDoesNotExist:
        return render(request, "404.html")

def robotstxt(request):
    lines = [
        "User-Agent: *",
        "Disallow: /admin/",
        "Disallow: /admin/*",
    ]

    return HttpResponse("\n".join(lines), content_type="text/plain")
