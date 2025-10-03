"""
Search utilities for blog posts, projects, and other content.
Provides full-text search and tag-based filtering.
"""
from django.db.models import Q, Count
from blog.models import Tag, BlogPostTag
from blog.utils import get_all_blog_posts, get_blog_from_template_name
from pages.utils import get_books


def search_blog_posts(query=None, tags=None, category=None):
    """
    Search blog posts by query string, tags, and/or category.
    
    Args:
        query: Search query string (searches titles and content)
        tags: List of tag slugs to filter by
        category: Blog category to filter by
        
    Returns:
        List of blog post dicts with metadata
    """
    all_posts = get_all_blog_posts()
    results = []
    
    for post_info in all_posts:
        template_name = post_info['template_name']
        post_category = post_info['category']
        
        # Category filter
        if category and post_category != category:
            continue
        
        # Get blog data
        try:
            blog_data = get_blog_from_template_name(
                template_name,
                load_content=bool(query),  # Only load content if searching text
                category=post_category
            )
        except Exception:
            continue
        
        # Tag filter
        if tags:
            post_tags = BlogPostTag.get_tags_for_post(template_name, post_category)
            post_tag_slugs = [tag.slug for tag in post_tags]
            
            # Check if post has all required tags
            if not all(tag_slug in post_tag_slugs for tag_slug in tags):
                continue
        
        # Text search filter
        if query:
            query_lower = query.lower()
            title_match = query_lower in blog_data['blog_title'].lower()
            content_match = query_lower in blog_data['blog_content'].lower()
            
            if not (title_match or content_match):
                continue
        
        # Add tags to blog data
        blog_data['tags'] = BlogPostTag.get_tags_for_post(template_name, post_category)
        results.append(blog_data)
    
    # Sort by entry number (newest first)
    results.sort(key=lambda x: x['entry_number'], reverse=True)
    return results


def search_projects(query=None, tags=None):
    """
    Search projects by query string and/or technology tags.
    
    Args:
        query: Search query string (searches name and description)
        tags: List of technology names to filter by
        
    Returns:
        List of project dicts
    """
    from pages.views import home
    import inspect
    
    # Get projects from the home view (hardcoded list)
    source = inspect.getsource(home)
    
    # Extract projects from view code (this is a workaround for hardcoded projects)
    # In a real implementation, projects should be in a database
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
    
    results = []
    
    for project in projects:
        # Text search
        if query:
            query_lower = query.lower()
            name_match = query_lower in project['name'].lower()
            desc_match = query_lower in project['description'].lower()
            
            if not (name_match or desc_match):
                continue
        
        # Technology tag filter
        if tags:
            project_tech_lower = [t.lower() for t in project.get('tech', [])]
            tags_lower = [t.lower() for t in tags]
            
            if not all(tag in project_tech_lower for tag in tags_lower):
                continue
        
        results.append(project)
    
    return results


def search_books(query=None):
    """
    Search books by query string.
    
    Args:
        query: Search query string (searches name, author, and quote)
        
    Returns:
        List of book dicts
    """
    try:
        all_books = get_books()
    except Exception:
        return []
    
    if not query:
        return all_books
    
    results = []
    query_lower = query.lower()
    
    for book in all_books:
        name_match = query_lower in book.get('name', '').lower()
        author_match = query_lower in book.get('author', '').lower()
        quote_match = query_lower in book.get('favourite_quote', '').lower()
        
        if name_match or author_match or quote_match:
            results.append(book)
    
    return results


def get_all_tags_with_counts():
    """
    Get all tags with their usage counts.
    
    Returns:
        QuerySet of Tag objects annotated with post counts
    """
    return Tag.objects.annotate(
        post_count=Count('blog_posts')
    ).filter(
        post_count__gt=0
    ).order_by('-post_count', 'name')


def get_related_posts(template_name, category=None, limit=5):
    """
    Find related blog posts based on shared tags and category.
    
    Args:
        template_name: Current blog post template name
        category: Current blog post category
        limit: Maximum number of related posts to return
        
    Returns:
        List of related blog post dicts with relevance scores
    """
    # Get tags for the current post
    current_tags = BlogPostTag.get_tags_for_post(template_name, category)
    
    if not current_tags:
        # If no tags, return recent posts from same category
        all_posts = get_all_blog_posts()
        same_category_posts = [
            p for p in all_posts 
            if p['category'] == category and p['template_name'] != template_name
        ]
        same_category_posts.sort(key=lambda x: x['template_name'], reverse=True)
        
        results = []
        for post_info in same_category_posts[:limit]:
            try:
                blog_data = get_blog_from_template_name(
                    post_info['template_name'],
                    load_content=False,
                    category=post_info['category']
                )
                blog_data['relevance_score'] = 0.5  # Lower score for category-only match
                blog_data['shared_tags'] = []
                results.append(blog_data)
            except Exception:
                continue
        
        return results
    
    current_tag_ids = [tag.id for tag in current_tags]
    
    # Find posts that share tags
    related_tag_associations = BlogPostTag.objects.filter(
        tag_id__in=current_tag_ids
    ).exclude(
        blog_template_name=template_name,
        blog_category=category
    ).select_related('tag')
    
    # Calculate relevance scores
    post_scores = {}
    post_shared_tags = {}
    
    for assoc in related_tag_associations:
        key = (assoc.blog_template_name, assoc.blog_category)
        
        if key not in post_scores:
            post_scores[key] = 0
            post_shared_tags[key] = []
        
        post_scores[key] += 1
        post_shared_tags[key].append(assoc.tag)
    
    # Sort by relevance score
    sorted_posts = sorted(
        post_scores.items(),
        key=lambda x: (x[1], x[0][0]),  # Sort by score, then template name
        reverse=True
    )
    
    # Get blog data for top related posts
    results = []
    for (post_template, post_cat), score in sorted_posts[:limit]:
        try:
            blog_data = get_blog_from_template_name(
                post_template,
                load_content=False,
                category=post_cat
            )
            blog_data['relevance_score'] = score / len(current_tags)  # Normalize score
            blog_data['shared_tags'] = post_shared_tags[(post_template, post_cat)]
            blog_data['tags'] = BlogPostTag.get_tags_for_post(post_template, post_cat)
            results.append(blog_data)
        except Exception:
            continue
    
    return results

