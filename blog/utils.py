import datetime
import os
from django.conf import settings
from django.template.loader import render_to_string

def get_blog_from_template_name(template_name, load_content=True, category=None):
    """
    Get blog data from template name, searching across categories if needed.
    
    Args:
        template_name: Name of the blog template (without .html extension)
        load_content: Whether to render the template content (False for metadata only)
        category: Optional category hint to avoid searching
        
    Returns:
        Dict with blog metadata including title, content, category, and GitHub link
    """
    entry_number = template_name.split("_")[0]
    blog_title = template_name.replace("_", " ")  # Preserve original case
    
    # Determine template path based on category or search for it
    if category:
        template_path = f"blog/{category}/{template_name}.html"
    else:
        template_path = find_blog_template(template_name)
        if template_path:
            parts = template_path.split('/')
            if len(parts) > 2:  # Extract category from path like blog/category/file.html
                category = parts[1]
        else:
            template_path = f"blog/{template_name}.html"
    
    blog_content = render_to_string(template_path) if load_content else ""
    
    # Build GitHub history link based on file location
    if category:
        github_path = f"templates/blog/{category}/{template_name}.html"
    else:
        github_path = f"templates/blog/{template_name}.html"
    
    return {
        "entry_number": entry_number,
        "template_name": template_name,
        "blog_title": blog_title,
        "blog_content": blog_content,
        "category": category,
        "github_link": f"https://github.com/aaronspindler/aaronspindler.com/commits/main/{github_path}",
    }

def find_blog_template(template_name):
    """
    Find a blog template by name, searching through all categories.
    
    Searches first in the root blog directory, then in category subdirectories.
    
    Args:
        template_name: Name of the template file (without .html extension)
        
    Returns:
        Relative template path for Django's template loader, or None if not found
    """
    blog_templates_path = os.path.join(settings.BASE_DIR, 'templates', 'blog')
    
    # Check root blog directory first
    root_path = os.path.join(blog_templates_path, f'{template_name}.html')
    if os.path.exists(root_path):
        return f"blog/{template_name}.html"
    
    # Search in category subdirectories
    for category in os.listdir(blog_templates_path):
        category_path = os.path.join(blog_templates_path, category)
        if os.path.isdir(category_path):
            file_path = os.path.join(category_path, f'{template_name}.html')
            if os.path.exists(file_path):
                return f"blog/{category}/{template_name}.html"
    
    return None

def get_all_blog_posts():
    """
    Scan the blog templates directory to find all blog posts.
    
    Walks through the blog directory structure and collects all HTML templates,
    organizing them by category (subdirectory).
    
    Returns:
        List of dicts with template_name, category, and full_path for each blog post
    """
    blog_posts = []
    blog_templates_path = os.path.join(settings.BASE_DIR, 'templates', 'blog')
    
    for root, dirs, files in os.walk(blog_templates_path):
        rel_path = os.path.relpath(root, blog_templates_path)
        
        # Determine category based on directory structure
        if rel_path == '.':
            category = None  # Root level posts have no category
        else:
            category = rel_path.split(os.sep)[0]  # First directory is the category
        
        for file in files:
            if file.endswith('.html'):
                template_name = file[:-5]  # Remove .html extension
                blog_posts.append({
                    'template_name': template_name,
                    'category': category,
                    'full_path': os.path.join(root, file)
                })
    
    return blog_posts
