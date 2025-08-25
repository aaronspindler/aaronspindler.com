from django.http import HttpResponse, JsonResponse
from django.template import TemplateDoesNotExist
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from pages.models import PageVisit
from blog.utils import get_blog_from_template_name, get_all_blog_posts
from blog.knowledge_graph import build_knowledge_graph, get_post_graph

import os
from django.conf import settings
import logging
import json
import asyncio
from io import BytesIO
from pathlib import Path
from django.core.cache import cache

logger = logging.getLogger(__name__)


def render_blog_template(request, template_name, category=None):
    """Render a blog post template."""
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
        
        # Get parameters from the request (with higher default resolution)
        width = int(request.GET.get('width', 2400))  # Doubled from 1200 for higher resolution
        height = int(request.GET.get('height', 1600))  # Doubled from 800 for higher resolution
        full_page = request.GET.get('full_page', 'false').lower() == 'true'
        wait_time = int(request.GET.get('wait_time', 10000))  # Increased from 3000 for better rendering
        
        # Build the full URL for the page with the knowledge graph
        host = request.get_host()
        protocol = 'https' if request.is_secure() else 'http'
        base_url = f"{protocol}://{host}"
        
        # Run Playwright to capture the screenshot
        with sync_playwright() as p:
            # Launch headless browser with Docker-compatible settings and high quality
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',  # Required for Docker
                    '--disable-setuid-sandbox',  # Required for Docker
                    '--disable-dev-shm-usage',  # Overcome limited resource problems
                    '--disable-gpu',  # Disable GPU hardware acceleration
                    '--single-process',  # Run in single process mode for containers
                    '--force-device-scale-factor=2.0',  # Force high DPI for better quality
                    '--high-dpi-support=1',  # Enable high DPI support
                    '--force-color-profile=srgb'  # Ensure consistent color profile
                ]
            )
            
            try:
                # Create a new page with specified viewport and high DPI settings
                context = browser.new_context(
                    viewport={'width': width, 'height': height},
                    device_scale_factor=2.0,  # Retina quality
                    screen={'width': width, 'height': height}  # Set screen size as well
                )
                page = context.new_page()
                
                # Navigate to the home page (where the knowledge graph is)
                page.goto(f"{base_url}/", wait_until='networkidle')
                
                # Wait for the knowledge graph container to be visible
                page.wait_for_selector('#knowledge-graph-container', state='visible', timeout=10000)
                
                # Wait for the SVG element to be present
                page.wait_for_selector('#knowledge-graph-svg', state='visible', timeout=10000)
                
                # Wait for the graph to render (check for nodes)
                page.wait_for_selector('#knowledge-graph-svg .node', state='visible', timeout=10000)
                
                # Additional wait to ensure animation and layout stabilization at high resolution
                # Use longer wait time for better quality rendering
                actual_wait_time = max(wait_time, 10000)  # Minimum 10 seconds for high res
                page.wait_for_timeout(actual_wait_time)
                
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
                
                # Take high-quality screenshot of the knowledge graph container
                if full_page:
                    screenshot = page.screenshot(
                        full_page=True,
                        animations='disabled',  # Disable animations for cleaner screenshot
                        scale='device'  # Use device scale factor for high DPI
                    )
                else:
                    # Get the knowledge graph element specifically
                    element = page.query_selector('#knowledge-graph-container')
                    if element:
                        screenshot = element.screenshot(
                            animations='disabled',  # Disable animations
                            scale='device',  # Use device scale factor
                            timeout=30000  # Longer timeout for large screenshots
                        )
                    else:
                        # Fallback to high-quality full page if element not found
                        screenshot = page.screenshot(
                            full_page=True,
                            animations='disabled',
                            scale='device'
                        )
                
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
