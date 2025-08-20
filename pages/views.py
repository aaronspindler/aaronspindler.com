from django.http import HttpResponse, JsonResponse
from django.template import TemplateDoesNotExist
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from pages.models import PageVisit
from pages.utils import get_blog_from_template_name, get_books, get_all_blog_posts
from pages.knowledge_graph import build_knowledge_graph, get_post_graph

import os
from django.conf import settings
import logging
import json
import asyncio
from io import BytesIO

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
        "link": "https://team.bio",
        "tech": ["Python", "Django", "PostgreSQL", "HTML", "JavaScript"]
    })
    projects.append({
        "name": "ActionsUptime",
        "description": "ActionsUptime is a platform to help you monitor your GitHub Actions and get notifications when they fail.",
        "link": "https://actionsuptime.com",
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
            "blog_posts_by_category": blog_posts_by_category,
            "projects": projects,
            "books": books
        }
    )


def render_blog_template(request, template_name, category=None):
    try:
        blog_data = get_blog_from_template_name(template_name, category=category)
        # Include category in the page name for tracking if available
        if category:
            page_name = f'/b/{category}/{template_name}/'
        else:
            page_name = f'/b/{template_name}/'
        views = PageVisit.objects.filter(page_name=page_name).values_list('pk', flat=True).count()
        blog_data['views'] = views
        return render(request, "_blog_base.html", blog_data)
    except TemplateDoesNotExist:
        return render(request, "404.html")

@require_http_methods(["GET", "POST"])
@csrf_exempt
def knowledge_graph_api(request):
    """API endpoint for knowledge graph data."""
    try:
        graph_data = _get_graph_data(request)
        
        response_data = {
            'status': 'success',
            'data': graph_data,
            'metadata': {
                'nodes_count': len(graph_data.get('nodes', [])),
                'edges_count': len(graph_data.get('edges', [])),
                'has_errors': bool(graph_data.get('errors', []))
            }
        }
        
        return JsonResponse(response_data)
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in knowledge graph API: {str(e)}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


def _get_graph_data(request):
    """Get graph data based on request parameters."""
    if request.method == "POST":
        data = json.loads(request.body) if request.body else {}
        operation = data.get('operation', 'full_graph')
        
        operations = {
            'refresh': lambda: build_knowledge_graph(force_refresh=True),
            'post_graph': lambda: _get_post_graph_from_data(data),
            'full_graph': lambda: build_knowledge_graph()
        }
        
        handler = operations.get(operation, operations['full_graph'])
        return handler()
    
    # GET request
    template_name = request.GET.get('post')
    if template_name:
        depth = int(request.GET.get('depth', 1))
        return get_post_graph(template_name, depth)
    
    force_refresh = request.GET.get('refresh', '').lower() == 'true'
    return build_knowledge_graph(force_refresh)


def _get_post_graph_from_data(data):
    """Helper to get post graph from POST data."""
    template_name = data.get('template_name')
    if not template_name:
        raise ValueError('template_name required for post_graph operation')
    
    depth = data.get('depth', 1)
    return get_post_graph(template_name, depth)


@require_http_methods(["GET"])
def knowledge_graph_screenshot(request):
    """Serve the cached knowledge graph screenshot if it exists, otherwise generate it dynamically on first request."""
    from pathlib import Path
    import hashlib
    from django.core.cache import cache
    
    # Create a cache key based on the current deployment (use settings or git hash)
    cache_key = 'knowledge_graph_screenshot_generated'
    
    # Check if a cached screenshot exists
    cached_screenshot_paths = [
        Path(settings.STATIC_ROOT) / 'images' / 'knowledge_graph_cached.png',  # Production path
        Path(settings.BASE_DIR) / 'staticfiles' / 'images' / 'knowledge_graph_cached.png',  # Alternative path
        Path(settings.BASE_DIR) / 'static' / 'images' / 'knowledge_graph_cached.png',  # Development path
    ]
    
    cached_screenshot = None
    for path in cached_screenshot_paths:
        if path.exists():
            cached_screenshot = path
            logger.info(f"Found cached knowledge graph screenshot at: {path}")
            break
    
    # If cached screenshot exists, serve it
    if cached_screenshot:
        try:
            with open(cached_screenshot, 'rb') as f:
                screenshot_data = f.read()
            
            response = HttpResponse(screenshot_data, content_type='image/png')
            response['Content-Disposition'] = 'inline; filename="knowledge_graph.png"'
            # Cache for a long time since it's a static file that updates only on deploy
            response['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
            return response
        except Exception as e:
            logger.error(f"Error reading cached screenshot: {str(e)}")
            # Fall through to generation
    
    # Check if we should generate the screenshot
    force_regenerate = request.GET.get('force_regenerate', 'false').lower() == 'true'
    
    # Check if screenshot generation is already in progress or has been attempted
    generation_status = cache.get(cache_key)
    
    if not force_regenerate and generation_status == 'failed':
        # If generation has failed before, don't retry automatically
        return JsonResponse({
            'error': 'Knowledge graph screenshot generation previously failed. Add ?force_regenerate=true to retry.'
        }, status=503)
    
    if not force_regenerate and generation_status == 'in_progress':
        # If generation is in progress, return a temporary response
        return JsonResponse({
            'error': 'Knowledge graph screenshot is being generated. Please try again in a few moments.'
        }, status=503)
    
    # If no cached screenshot exists and we haven't tried generating it yet, or force_regenerate is true,
    # generate it now at runtime
    logger.info("Generating knowledge graph screenshot at runtime...")
    
    # Mark generation as in progress
    cache.set(cache_key, 'in_progress', timeout=300)  # 5 minute timeout
    
    # Dynamic generation code (original implementation)
    # This is now only used if force_regenerate=true is passed as a query parameter
    try:
        # Import Playwright here to avoid issues if not installed
        from playwright.sync_api import sync_playwright
        
        # Get parameters from the request
        width = int(request.GET.get('width', 1200))
        height = int(request.GET.get('height', 800))
        full_page = request.GET.get('full_page', 'false').lower() == 'true'
        wait_time = int(request.GET.get('wait_time', 3000))  # milliseconds to wait for graph rendering
        
        # Build the full URL for the page with the knowledge graph
        host = request.get_host()
        protocol = 'https' if request.is_secure() else 'http'
        base_url = f"{protocol}://{host}"
        
        # Run Playwright to capture the screenshot
        with sync_playwright() as p:
            # Launch headless browser with Docker-compatible settings
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',  # Required for Docker
                    '--disable-setuid-sandbox',  # Required for Docker
                    '--disable-dev-shm-usage',  # Overcome limited resource problems
                    '--disable-gpu',  # Disable GPU hardware acceleration
                    '--single-process'  # Run in single process mode for containers
                ]
            )
            
            try:
                # Create a new page with specified viewport
                page = browser.new_page(viewport={'width': width, 'height': height})
                
                # Navigate to the home page (where the knowledge graph is)
                page.goto(f"{base_url}/", wait_until='networkidle')
                
                # Wait for the knowledge graph container to be visible
                page.wait_for_selector('#knowledge-graph-container', state='visible', timeout=10000)
                
                # Wait for the SVG element to be present
                page.wait_for_selector('#knowledge-graph-svg', state='visible', timeout=10000)
                
                # Wait for the graph to render (check for nodes)
                page.wait_for_selector('#knowledge-graph-svg .node', state='visible', timeout=10000)
                
                # Additional wait to ensure animation and layout stabilization
                page.wait_for_timeout(wait_time)
                
                # Optionally zoom out to fit the entire graph
                if request.GET.get('fit_view', 'true').lower() == 'true':
                    # Trigger the fit view function
                    page.evaluate("""
                        if (window.homepageGraph && typeof window.homepageGraph.fitGraphToView === 'function') {
                            window.homepageGraph.fitGraphToView();
                        }
                    """)
                    # Wait a bit for the zoom animation
                    page.wait_for_timeout(500)
                
                # Take screenshot of the knowledge graph container
                if full_page:
                    screenshot = page.screenshot(full_page=True)
                else:
                    # Get the knowledge graph element specifically
                    element = page.query_selector('#knowledge-graph-container')
                    if element:
                        screenshot = element.screenshot()
                    else:
                        # Fallback to full page if element not found
                        screenshot = page.screenshot()
                
                # Save the screenshot to cache location for future use
                try:
                    # Ensure the directory exists
                    cache_dir = Path(settings.STATIC_ROOT) / 'images'
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    
                    cache_file = cache_dir / 'knowledge_graph_cached.png'
                    with open(cache_file, 'wb') as f:
                        f.write(screenshot)
                    
                    logger.info(f"Screenshot cached at: {cache_file}")
                    
                    # Mark generation as successful
                    cache.set(cache_key, 'success', timeout=86400)  # Cache for 24 hours
                    
                except Exception as save_error:
                    logger.error(f"Could not save screenshot to cache: {save_error}")
                    # Still return the screenshot even if caching failed
                
                # Return the screenshot as PNG
                response = HttpResponse(screenshot, content_type='image/png')
                response['Content-Disposition'] = 'inline; filename="knowledge_graph.png"'
                response['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
                
                return response
                
            finally:
                browser.close()
                
    except ImportError:
        logger.error("Playwright is not installed. Please install it with: pip install playwright && playwright install chromium")
        # Mark generation as failed
        cache.set(cache_key, 'failed', timeout=3600)  # Cache failure for 1 hour
        return JsonResponse({
            'error': 'Playwright is not installed. Please install it with: pip install playwright && playwright install chromium'
        }, status=500)
    except Exception as e:
        logger.error(f"Error generating knowledge graph screenshot: {str(e)}")
        # Mark generation as failed
        cache.set(cache_key, 'failed', timeout=3600)  # Cache failure for 1 hour
        return JsonResponse({'error': f'Failed to generate screenshot: {str(e)}'}, status=500)



