from django.http import HttpResponse
from django.shortcuts import render

from pages.models import PageVisit
from pages.utils import get_books
from pages.decorators import track_page_visit
from blog.utils import get_all_blog_posts, get_blog_from_template_name

import logging

import os
from django.conf import settings

logger = logging.getLogger(__name__)

def robotstxt(request):
    """Serve robots.txt from static file."""
    robots_path = os.path.join(settings.BASE_DIR, 'static', 'robots.txt')
    
    with open(robots_path, 'r') as f:
        content = f.read()
    return HttpResponse(content, content_type="text/plain")

@track_page_visit
def home(request):
    logger.info("Home page requested")
    # Blog - Get all blog posts from all categories
    all_posts = get_all_blog_posts()
    blog_posts = []
    blog_posts_by_category = {}  # Organize posts by category
    
    for post_info in all_posts:
        blog_data = get_blog_from_template_name(
            post_info['template_name'], 
            load_content=False, 
            category=post_info['category']
        )
        blog_posts.append(blog_data)
        
        # Organize by category
        category = post_info['category'] or 'uncategorized'
        if category not in blog_posts_by_category:
            blog_posts_by_category[category] = []
        blog_posts_by_category[category].append(blog_data)
    
    # Sort posts within each category
    for category in blog_posts_by_category:
        blog_posts_by_category[category].sort(key=lambda x: x['entry_number'], reverse=True)
    
    # Sort all posts for backward compatibility
    blog_posts.sort(key=lambda x: x['entry_number'], reverse=True)
    
    # Projects
    projects = []
    projects.append({
        "name": "Team Bio",
        "description": "Team Bio is a platform to foster professional connections between coworkers within a company. This is done with profiles, trivia, coffee chats, and more.",
        "link": "https://github.com/aaronspindler/Team.Bio",
        "tech": ["Python", "Django", "PostgreSQL", "HTML", "JavaScript"]
    })
    projects.append({
        "name": "ActionsUptime",
        "description": "ActionsUptime is a platform to help you monitor your GitHub Actions and get notifications when they fail.",
        "tech": ["Django", "PostgreSQL", "Celery", "Redis"]
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
        "link": "https://spindlers.ca",
        "tech": ["Software Development", "Web Design", "Graphic Design", "SEO", "Marketing", "Consulting"]
    })
    
    # Books
    books = get_books()
    
    return render(
        request,
        "pages/home.html",
        {
            "blog_posts": blog_posts,
            "blog_posts_by_category": blog_posts_by_category,
            "projects": projects,
            "books": books
        }
    )