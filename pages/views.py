from django.http import HttpResponse, JsonResponse
from django.template import TemplateDoesNotExist
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from pages.models import PageVisit
from pages.utils import get_blog_from_template_name, get_books
from pages.knowledge_graph import build_knowledge_graph, get_post_graph

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

@require_http_methods(["GET", "POST"])
@csrf_exempt
def knowledge_graph_api(request):
    """API endpoint for knowledge graph data."""
    try:
        if request.method == "POST":
            # Handle POST requests for specific operations
            data = json.loads(request.body) if request.body else {}
            operation = data.get('operation', 'full_graph')
            
            if operation == 'refresh':
                graph_data = build_knowledge_graph(force_refresh=True)
            elif operation == 'post_graph':
                template_name = data.get('template_name')
                depth = data.get('depth', 1)
                if not template_name:
                    return JsonResponse({'error': 'template_name required for post_graph operation'}, status=400)
                graph_data = get_post_graph(template_name, depth)
            else:
                graph_data = build_knowledge_graph()
        else:
            # GET request - return full graph
            force_refresh = request.GET.get('refresh', '').lower() == 'true'
            template_name = request.GET.get('post')
            
            if template_name:
                depth = int(request.GET.get('depth', 1))
                graph_data = get_post_graph(template_name, depth)
            else:
                graph_data = build_knowledge_graph(force_refresh)
        
        # Add metadata
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
        
    except Exception as e:
        logger.error(f"Error in knowledge graph API: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)



