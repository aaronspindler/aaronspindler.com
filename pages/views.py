from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.shortcuts import render

from pages.models import PageVisit
from pages.utils import get_blog_from_template_name, get_books

import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def robotstxt(request):
    lines = [
        "User-Agent: *",
        "Disallow: /admin/",
        "Disallow: /admin/*",
    ]

    return HttpResponse("\n".join(lines), content_type="text/plain")

def home(request):
    logger.info("Home page requested")
    # Blog
    blog_posts = []
    blog_templates_path = os.path.join(settings.BASE_DIR, 'templates', 'blog')
    for template_name in os.listdir(blog_templates_path):
        if template_name.endswith('.html'):
            template_name = template_name.split('.')[0]
            blog_posts.append(get_blog_from_template_name(template_name))
    blog_posts.sort(key=lambda x: x['created_timestamp'], reverse=True)
    
    # Projects
    projects = []
    projects.append({
        "name": "Team Bio",
        "description": "Team Bio is a platform to foster professional connections between coworkers within a company. This is done with profiles, trivia, coffee chats, and more.",
        "link": "https://team.bio",
        "tech": ["Python", "Django", "PostgreSQL", "HTML", "JavaScript"]
    })
    projects.append({
        "name": "Poseidon",
        "description": "Poseidon is a tool to help explore financial data, generate insights, and make trading decisions.",
        "link": "https://github.com/aaronspindler/Poseidon",
        "tech": ["Python", "Django", "PostgreSQL", "C#", "Prophet", "Various ML/AI models"]
    })
    projects.append({
        "name": "Spindlers",
        "description": "Spindlers is a full service technology consulting company, specializing in custom software solutions, web development, and bringing small/medium businesses into the digital age.",
        "link": "https://spindlers.co",
        "tech": ["Software Development", "Web Design", "Graphic Design", "SEO", "Marketing", "Consulting"]
    })
    
    # Books
    books = get_books()
    
    return render(
        request,
        "pages/home.html",
        {
            "blog_posts": blog_posts,
            "projects": projects,
            "books": books
        }
    )


def render_blog_template(request, template_name):
    try:
        blog_data = get_blog_from_template_name(template_name)
        views = PageVisit.objects.filter(page_name=f'/b/{template_name}/').values_list('pk', flat=True).count()
        blog_data['views'] = views
        return render(request, "_blog_base.html", blog_data)
    except TemplateDoesNotExist:
        return render(request, "404.html")
