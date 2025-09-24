from django.http import HttpResponse, JsonResponse, Http404, FileResponse
from django.shortcuts import render
from django.core.cache import cache
from django.db import connection
from django.db.models import Count

from pages.models import PageVisit
from pages.utils import get_books
from pages.decorators import track_page_visit
from blog.utils import get_all_blog_posts, get_blog_from_template_name
from photos.models import PhotoAlbum

import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

def health_check(request):
    """
    Simple health check endpoint for monitoring.
    Returns 200 OK if the application is running and can connect to the database.
    """
    health_status = {
        "status": "healthy",
        "checks": {}
    }
    
    # Check database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        logger.error(f"Health check database error: {e}")
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = "failed"
        return JsonResponse(health_status, status=503)
    
    # Check cache connectivity (optional, non-critical)
    try:
        cache.set("health_check", "test", 1)
        cache.delete("health_check")
        health_status["checks"]["cache"] = "ok"
    except Exception as e:
        logger.warning(f"Health check cache error: {e}")
        health_status["checks"]["cache"] = "unavailable"
    
    return JsonResponse(health_status)


def robotstxt(request):
    """Serve robots.txt from static file."""
    robots_path = os.path.join(settings.BASE_DIR, 'static', 'robots.txt')
    
    with open(robots_path, 'r') as f:
        content = f.read()
    return HttpResponse(content, content_type="text/plain")


@track_page_visit
def resume(request):
    """Serve resume PDF file if enabled in settings, otherwise show unavailable page."""
    if not getattr(settings, 'RESUME_ENABLED', False):
        return render(request, 'pages/resume_unavailable.html')
    
    resume_filename = getattr(settings, 'RESUME_FILENAME', 'Aaron_Spindler_Resume_2025.pdf')
    resume_path = os.path.join(settings.BASE_DIR, 'static', 'files', resume_filename)
    
    if not os.path.exists(resume_path):
        logger.error(f"Resume file not found at: {resume_path}")
        raise Http404("Resume file not found")
    
    try:
        response = FileResponse(
            open(resume_path, 'rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'inline; filename="{resume_filename}"'
        return response
    except Exception as e:
        logger.error(f"Error serving resume file: {e}")
        raise Http404("Error serving resume")

@track_page_visit
def home(request):
    """
    Display home page with blog posts, projects, books, and photo albums.
    Uses caching for performance optimization.
    """
    logger.info("Home page requested")
    
    # Cache blog posts (1 hour TTL)
    blog_cache_key = 'home_blog_posts_v2'
    cached_blog_data = cache.get(blog_cache_key)
    
    if cached_blog_data:
        blog_posts = cached_blog_data['blog_posts']
        blog_posts_by_category = cached_blog_data['blog_posts_by_category']
    else:
        all_posts = get_all_blog_posts()
        blog_posts = []
        blog_posts_by_category = {}
        
        for post_info in all_posts:
            blog_data = get_blog_from_template_name(
                post_info['template_name'], 
                load_content=False,  # Don't load content for listing
                category=post_info['category']
            )
            blog_posts.append(blog_data)
            
            # Organize by category
            category = post_info['category'] or 'uncategorized'
            if category not in blog_posts_by_category:
                blog_posts_by_category[category] = []
            blog_posts_by_category[category].append(blog_data)
        
        # Sort posts within each category by entry number (newest first)
        for category in blog_posts_by_category:
            blog_posts_by_category[category].sort(key=lambda x: x['entry_number'], reverse=True)
        
        blog_posts.sort(key=lambda x: x['entry_number'], reverse=True)
        
        cache.set(blog_cache_key, {
            'blog_posts': blog_posts,
            'blog_posts_by_category': blog_posts_by_category
        }, 3600)
    
    # Projects (24 hour cache)
    projects_cache_key = 'home_projects_v1'
    projects = cache.get(projects_cache_key)
    
    if not projects:
        projects = [
            {
                "name": "Team Bio",
                "description": "Team Bio is a platform to foster professional connections between coworkers within a company. This is done with profiles, trivia, coffee chats, and more.",
                "link": "https://github.com/aaronspindler/Team.Bio",
                "tech": ["Python", "Django", "PostgreSQL", "HTML", "JavaScript"]
            },
            {
                "name": "ActionsUptime",
                "description": "ActionsUptime is a platform to help you monitor your GitHub Actions and get notifications when they fail.",
                "tech": ["Django", "PostgreSQL", "Celery", "Redis"]
            },
            {
                "name": "Poseidon",
                "description": "Poseidon is a tool to help explore financial data, generate insights, and make trading decisions.",
                "link": "https://github.com/aaronspindler/Poseidon",
                "tech": ["Python", "Django", "PostgreSQL", "C#", "Prophet", "Various ML/AI models"]
            },
            {
                "name": "Spindlers",
                "description": "Spindlers is a full service technology consulting company, specializing in custom software solutions, web development, and bringing small/medium businesses into the digital age.",
                "link": "https://spindlers.ca",
                "tech": ["Software Development", "Web Design", "Graphic Design", "SEO", "Marketing", "Consulting"]
            },
            {
                "name": "iMessageLLM",
                "description": "iMessageLLM brings the power of large language models directly to your iMessage conversations, understand context, summarize years of message history, and extract key insights.",
                "link": "https://github.com/aaronspindler/iMessageLLM",
                "tech": ["Python", "LLMs", "Data Analysis", "iMessage"]
            },
            {
                "name": "Lightroom Blur",
                "description": "Clean up unintentionally blurry and duplicate photos in Lightroom and Apple Photos automatically with AI-powered image classification and blur detection.",
                "link": "https://github.com/aaronspindler/lightroom",
                "tech": ["Python", "Image Processing", "Machine Learning", "Blur Detection", "Apple Photos", "Lightroom"]
            }
        ]
        cache.set(projects_cache_key, projects, 86400)  # Cache for 24 hours
    
    # Books (24 hour cache)
    books_cache_key = 'home_books_v1'
    books = cache.get(books_cache_key)
    
    if not books:
        books = get_books()
        cache.set(books_cache_key, books, 86400)
    
    # Photo Albums - Get public albums with annotated photo counts for efficiency
    albums = PhotoAlbum.objects.filter(is_private=False).annotate(
        photo_count=Count('photos')
    ).order_by('-created_at')
    
    album_data = []
    for album in albums:
        # Get random cover photo using database-level selection
        cover_photo = album.photos.order_by('?').first()
        album_data.append({
            'album': album,
            'cover_photo': cover_photo,
            'photo_count': album.photo_count
        })
    
    return render(
        request,
        "pages/home.html",
        {
            "blog_posts": blog_posts,
            "blog_posts_by_category": blog_posts_by_category,
            "projects": projects,
            "books": books,
            "album_data": album_data
        }
    )