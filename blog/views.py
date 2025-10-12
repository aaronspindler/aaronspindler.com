from django.http import HttpResponse, JsonResponse
from django.template import TemplateDoesNotExist
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_GET
from django.contrib import messages

from blog.utils import get_blog_from_template_name
from blog.knowledge_graph import build_knowledge_graph, get_post_graph
from blog.models import BlogComment, CommentVote, KnowledgeGraphScreenshot
from blog.forms import CommentForm, ReplyForm
from blog.search import search_blog_posts, search_projects, search_books

import logging
import json

logger = logging.getLogger(__name__)


def render_blog_template(request, category, template_name):
    """
    Render a blog post with comments, voting, and view tracking.
    
    This view handles the main blog post display, including:
    - Loading the blog template content
    - Fetching and organizing approved comments
    - Adding user vote data for authenticated users
    - Providing comment forms and moderation info for staff
    """
    try:
        blog_data = get_blog_from_template_name(template_name, category=category)
        
        # Build page path for view tracking using RequestFingerprint
        page_path = f'/b/{category}/{template_name}/'
        
        from utils.models import RequestFingerprint
        views = RequestFingerprint.objects.filter(path=page_path).count()
        blog_data['views'] = views
        
        # Fetch approved comments with optimized queries
        comments = BlogComment.get_approved_comments(template_name, category)
        
        # Annotate comments with user's votes if authenticated
        if request.user.is_authenticated:
            for comment in comments:
                comment.user_vote = comment.get_user_vote(request.user)
                # Recursively add vote info to nested replies
                for reply in comment.get_replies():
                    reply.user_vote = reply.get_user_vote(request.user)
        
        blog_data['comments'] = comments
        blog_data['comment_count'] = comments.count()
        blog_data['comment_form'] = CommentForm(user=request.user)
        
        # Show pending comment count to staff for moderation
        if request.user.is_staff:
            blog_data['pending_comments_count'] = BlogComment.objects.filter(
                blog_template_name=template_name,
                blog_category=category,
                status='pending'
            ).count()
        
        return render(request, "_blog_base.html", blog_data)
    except (TemplateDoesNotExist, Exception):
        # Handle both template not found and other errors
        from django.http import Http404
        raise Http404("Blog post not found")


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
        logger.error(f"ValueError in knowledge graph API: {str(e)}")
        return JsonResponse({'error': 'Invalid request data'}, status=400)
    except Exception as e:
        logger.error(f"Error in knowledge graph API: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'error': 'An error occurred while processing your request'}, status=500)


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
    """
    Serve a screenshot of the knowledge graph from the database.
    
    Screenshots are generated via the management command:
    python manage.py generate_knowledge_graph_screenshot
    """
    try:
        # Get the most recently updated screenshot from database
        screenshot_obj = KnowledgeGraphScreenshot.objects.latest('updated_at')
        
        if screenshot_obj and screenshot_obj.image:
            # Serve the screenshot from the database
            try:
                response = HttpResponse(screenshot_obj.image.read(), content_type='image/png')
                response['Content-Disposition'] = 'inline; filename="knowledge_graph.png"'
                # Prevent caching of the knowledge graph image
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                return response
            except Exception as e:
                logger.error(f"Error reading screenshot from database: {str(e)}")
                return JsonResponse({
                    'error': 'Failed to read screenshot from database.'
                }, status=500)
    
    except KnowledgeGraphScreenshot.DoesNotExist:
        # No screenshot available
        pass
    
    # Return error if no screenshot is available
    return JsonResponse({
        'error': 'Knowledge graph screenshot not available. Please run the management command: python manage.py generate_knowledge_graph_screenshot'
    }, status=404)


def submit_comment(request, category, template_name):
    """
    Process comment submission with spam protection and moderation.
    
    Handles both authenticated and anonymous comments, applies spam detection,
    and routes comments through the moderation pipeline.
    """
    if request.method != 'POST':
        return redirect('render_blog_template', category=category, template_name=template_name)
    
    form = CommentForm(request.POST, user=request.user)
    
    if form.is_valid():
        # Collect metadata for spam detection
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        comment = form.save(
            blog_template_name=template_name,
            blog_category=category,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Provide feedback based on moderation status
        if comment.status == 'approved':
            messages.success(request, 'Your comment has been posted!')
        else:
            messages.info(request, 'Your comment has been submitted for review and will appear after approval.')
        
        # Redirect to comments section
        from django.urls import reverse
        url = reverse('render_blog_template', kwargs={'category': category, 'template_name': template_name})
        return redirect(url + '#comments')
    
    # Re-render page with form errors if validation failed
    try:
        blog_data = get_blog_from_template_name(template_name, category=category)
        page_path = f'/b/{category}/{template_name}/'
        
        from utils.models import RequestFingerprint
        views = RequestFingerprint.objects.filter(path=page_path).count()
        blog_data['views'] = views
        
        comments = BlogComment.get_approved_comments(template_name, category)
        blog_data['comments'] = comments
        blog_data['comment_count'] = comments.count()
        blog_data['comment_form'] = form  # Include form with validation errors
        
        return render(request, "_blog_base.html", blog_data)
    except Exception:
        # If blog template doesn't exist, return 404
        from django.http import Http404
        raise Http404("Blog post not found")


def reply_to_comment(request, comment_id):
    """
    Handle threaded replies to comments with spam protection.
    
    Supports nested comment threads while maintaining the same
    spam protection and moderation workflow as top-level comments.
    """
    parent_comment = get_object_or_404(BlogComment, id=comment_id, status='approved')
    
    if request.method != 'POST':
        from django.urls import reverse
        url = reverse('render_blog_template', kwargs={
            'category': parent_comment.blog_category,
            'template_name': parent_comment.blog_template_name
        })
        return redirect(url + f'#comment-{comment_id}')
    
    # Honeypot check for bot protection
    if request.POST.get('website', ''):
        messages.error(request, 'Bot detection triggered.')
        from django.urls import reverse
        url = reverse('render_blog_template', kwargs={
            'category': parent_comment.blog_category,
            'template_name': parent_comment.blog_template_name
        })
        return redirect(url + f'#comment-{comment_id}')
    
    form = ReplyForm(request.POST, user=request.user)
    
    if form.is_valid():
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        reply = form.save(
            blog_template_name=parent_comment.blog_template_name,
            blog_category=parent_comment.blog_category,
            parent=parent_comment,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if reply.status == 'approved':
            messages.success(request, 'Your reply has been posted!')
        else:
            messages.info(request, 'Your reply has been submitted for review.')
    else:
        messages.error(request, 'There was an error with your reply. Please try again.')
    
    # Return to parent comment location
    from django.urls import reverse
    url = reverse('render_blog_template', kwargs={
        'category': parent_comment.blog_category,
        'template_name': parent_comment.blog_template_name
    })
    return redirect(url + f'#comment-{comment_id}')


@require_http_methods(["POST"])
def moderate_comment(request, comment_id):
    """Handle comment moderation (staff only)."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    comment = get_object_or_404(BlogComment, id=comment_id)
    action = request.POST.get('action')
    
    if action == 'approve':
        comment.approve(user=request.user)
        messages.success(request, f'Comment by {comment.get_author_display()} approved.')
    elif action == 'reject':
        note = request.POST.get('note', '')
        comment.reject(user=request.user, note=note)
        messages.warning(request, f'Comment by {comment.get_author_display()} rejected.')
    elif action == 'spam':
        comment.mark_as_spam(user=request.user)
        messages.warning(request, f'Comment by {comment.get_author_display()} marked as spam.')
    else:
        return JsonResponse({'error': 'Invalid action'}, status=400)
    
    # Return JSON response for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'new_status': comment.status,
            'message': f'Comment {action}ed successfully'
        })
    
    # Otherwise redirect back
    return redirect(f'/b/{comment.blog_category}/{comment.blog_template_name}/#comments')


def delete_comment(request, comment_id):
    """Delete a comment (author or staff only)."""
    comment = get_object_or_404(BlogComment, id=comment_id)
    
    # Check permissions
    can_delete = (
        request.user.is_staff or 
        (request.user.is_authenticated and comment.author == request.user)
    )
    
    if not can_delete:
        messages.error(request, 'You do not have permission to delete this comment.')
        return redirect(f'/b/{comment.blog_category}/{comment.blog_template_name}/#comments')
    
    # Store blog info before deletion
    template_name = comment.blog_template_name
    category = comment.blog_category
    
    # Delete the comment (will cascade delete replies)
    comment.delete()
    messages.success(request, 'Comment deleted successfully.')
    
    # Redirect back to blog post
    return redirect(f'/b/{category}/{template_name}/#comments')


@require_http_methods(["POST"])
def vote_comment(request, comment_id):
    """
    Handle comment voting with toggle functionality.
    
    This view implements a three-state voting system:
    1. No vote -> Add vote
    2. Same vote -> Remove vote (toggle off)
    3. Different vote -> Change vote
    
    Vote counts are cached on the comment model and updated automatically.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        comment = BlogComment.objects.get(id=comment_id, status='approved')
    except BlogComment.DoesNotExist:
        return JsonResponse({'error': 'Comment not found'}, status=404)
    
    vote_type = request.POST.get('vote_type')
    if vote_type not in ['upvote', 'downvote']:
        return JsonResponse({'error': 'Invalid vote type'}, status=400)
    
    # Handle vote logic: toggle, change, or create
    try:
        existing_vote = CommentVote.objects.get(comment=comment, user=request.user)
        
        if existing_vote.vote_type == vote_type:
            # Toggle: Remove vote if clicking same button
            existing_vote.delete()
            action = 'removed'
            user_vote = None
        else:
            # Change: Switch from upvote to downvote or vice versa
            existing_vote.vote_type = vote_type
            existing_vote.save()
            action = 'changed'
            user_vote = vote_type
    except CommentVote.DoesNotExist:
        # New vote
        CommentVote.objects.create(
            comment=comment,
            user=request.user,
            vote_type=vote_type,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        action = 'added'
        user_vote = vote_type
    
    # Refresh cached counts
    comment.update_vote_counts()
    comment.refresh_from_db()
    
    return JsonResponse({
        'status': 'success',
        'action': action,
        'upvotes': comment.upvotes,
        'downvotes': comment.downvotes,
        'score': comment.score,
        'user_vote': user_vote
    })


@require_GET
def search_view(request):
    """
    Unified search view for blog posts, projects, and books.
    Supports full-text search.
    """
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip() or None
    content_type = request.GET.get('type', 'all')  # all, blog, projects, books
    
    results = {
        'blog_posts': [],
        'projects': [],
        'books': []
    }
    
    # Search blog posts
    if content_type in ['all', 'blog']:
        results['blog_posts'] = search_blog_posts(
            query=query if query else None,
            category=category
        )
    
    # Search projects
    if content_type in ['all', 'projects']:
        results['projects'] = search_projects(
            query=query if query else None
        )
    
    # Search books
    if content_type in ['all', 'books']:
        results['books'] = search_books(
            query=query if query else None
        )
    
    context = {
        'query': query,
        'category': category,
        'content_type': content_type,
        'results': results,
        'total_results': len(results['blog_posts']) + len(results['projects']) + len(results['books'])
    }
    
    return render(request, 'blog/search_results.html', context)


@require_GET
def search_autocomplete(request):
    """
    API endpoint for search autocomplete suggestions.
    Returns top results from blog posts, projects, and books.
    """
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    suggestions = []
    
    # Get blog post suggestions (limit to 5)
    blog_posts = search_blog_posts(query=query)[:5]
    for post in blog_posts:
        suggestions.append({
            'title': post['blog_title'],
            'type': 'Blog Post',
            'url': f"/b/{post['category']}/{post['template_name']}/",
            'category': post['category']
        })
    
    # Get project suggestions (limit to 3)
    projects = search_projects(query=query)[:3]
    for project in projects:
        suggestions.append({
            'title': project['name'],
            'type': 'Project',
            'url': project.get('link', '#'),
            'external': bool(project.get('link'))
        })
    
    # Get book suggestions (limit to 2)
    books = search_books(query=query)[:2]
    for book in books:
        author_text = f" by {book['author']}" if book.get('author') else ""
        suggestions.append({
            'title': f"{book['name']}{author_text}",
            'type': 'Book',
            'url': '/#books'
        })
    
    return JsonResponse({'suggestions': suggestions[:10]})
