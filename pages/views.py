import logging
import os

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import Count
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render

from blog.utils import get_all_blog_posts, get_blog_from_template_name
from pages.utils import get_books, get_projects
from photos.models import PhotoAlbum

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Simple health check endpoint for monitoring.
    Returns 200 OK if the application is running and can connect to the database.
    """
    health_status = {"status": "healthy", "checks": {}}

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
    robots_path = os.path.join(settings.BASE_DIR, "static", "robots.txt")

    with open(robots_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HttpResponse(content, content_type="text/plain")


def resume(request):
    """Serve resume PDF file if enabled in settings, otherwise show unavailable page."""
    if not getattr(settings, "RESUME_ENABLED", False):
        return render(request, "pages/resume_unavailable.html")

    resume_filename = getattr(settings, "RESUME_FILENAME", "Aaron_Spindler_Resume_2025.pdf")
    resume_path = os.path.join(settings.BASE_DIR, "static", "files", resume_filename)

    if not os.path.exists(resume_path):
        logger.error(f"Resume file not found at: {resume_path}")
        raise Http404("Resume file not found")

    try:
        response = FileResponse(open(resume_path, "rb"), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{resume_filename}"'
        return response
    except Exception as e:
        logger.error(f"Error serving resume file: {e}")
        raise Http404("Error serving resume") from None


def home(request):
    """
    Display home page with blog posts, projects, books, and photo albums.
    """
    # Cache blog posts (1 hour TTL)
    blog_cache_key = "home_blog_posts_v2"
    cached_blog_data = cache.get(blog_cache_key)

    if cached_blog_data:
        blog_posts = cached_blog_data["blog_posts"]
        blog_posts_by_category = cached_blog_data["blog_posts_by_category"]
    else:
        all_posts = get_all_blog_posts()
        blog_posts = []
        blog_posts_by_category = {}

        for post_info in all_posts:
            blog_data = get_blog_from_template_name(
                post_info["template_name"],
                load_content=False,  # Don't load content for listing
                category=post_info["category"],
            )
            blog_posts.append(blog_data)

            # Organize by category
            category = post_info["category"] or "uncategorized"
            if category not in blog_posts_by_category:
                blog_posts_by_category[category] = []
            blog_posts_by_category[category].append(blog_data)

        # Sort posts within each category by entry number (newest first)
        for category in blog_posts_by_category:
            blog_posts_by_category[category].sort(key=lambda x: x["entry_number"], reverse=True)

        blog_posts.sort(key=lambda x: x["entry_number"], reverse=True)

        cache.set(
            blog_cache_key,
            {
                "blog_posts": blog_posts,
                "blog_posts_by_category": blog_posts_by_category,
            },
            3600,
        )

    # Projects (24 hour cache)
    projects_cache_key = "home_projects_v1"
    projects = cache.get(projects_cache_key)

    if not projects:
        try:
            projects = get_projects()
            cache.set(projects_cache_key, projects, 86400)  # Cache for 24 hours
        except Exception:
            # Handle errors gracefully - provide empty list as fallback
            projects = []

    # Books (24 hour cache)
    books_cache_key = "home_books_v1"
    books = cache.get(books_cache_key)

    if not books:
        try:
            books = get_books()
            cache.set(books_cache_key, books, 86400)
        except Exception:
            # Handle errors gracefully - provide empty list as fallback
            books = []

    # Photo Albums (24 hour cache)
    albums_cache_key = "home_albums_v1"
    album_data = cache.get(albums_cache_key)

    if not album_data:
        try:
            albums = (
                PhotoAlbum.objects.filter(is_private=False)
                .annotate(photo_count=Count("photos"))
                .order_by("-created_at")
            )

            album_data = []
            for album in albums:
                # Get random cover photo using database-level selection
                cover_photo = album.photos.order_by("?").first()
                album_data.append(
                    {
                        "album": album,
                        "cover_photo": cover_photo,
                        "photo_count": album.photo_count,
                    }
                )
            cache.set(albums_cache_key, album_data, 86400)  # Cache for 24 hours
        except Exception:
            album_data = []

    return render(
        request,
        "pages/home.html",
        {
            "blog_posts": blog_posts,
            "blog_posts_by_category": blog_posts_by_category,
            "projects": projects,
            "books": books,
            "album_data": album_data,
        },
    )
