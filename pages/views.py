from django.http import HttpResponse, JsonResponse
from django.template import TemplateDoesNotExist
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from pages.models import PageVisit
from pages.utils import get_blog_from_template_name, get_books
from pages.knowledge_graph import build_knowledge_graph, get_post_graph
from photos.models import Album

import os
from django.conf import settings
import logging
import json

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
            blog_posts.append(get_blog_from_template_name(template_name, load_content=False))
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
    
    # Albums - Get the 6 most recent published albums
    albums = Album.objects.filter(
        is_published=True
    ).prefetch_related('photos').order_by('order', '-created_at')[:6]
    
    return render(
        request,
        "pages/home.html",
        {
            "blog_posts": blog_posts,
            "projects": projects,
            "books": books,
            "albums": albums
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



