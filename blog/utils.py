import datetime
import os
from django.conf import settings
from django.template.loader import render_to_string

def get_blog_from_template_name(template_name, load_content=True, category=None):
    """Get blog data from template name, with optional category."""
    # Extract entry number and title
    entry_number = template_name.split("_")[0]
    blog_title = template_name.replace("_", " ").title()
    
    # Determine the template path based on category
    if category:
        template_path = f"blog/{category}/{template_name}.html"
    else:
        # Try to find the template in any category
        template_path = find_blog_template(template_name)
        if template_path:
            # Extract category from the found path
            parts = template_path.split('/')
            if len(parts) > 2:  # blog/category/filename.html
                category = parts[1]
        else:
            template_path = f"blog/{template_name}.html"  # fallback
    
    blog_content = render_to_string(template_path) if load_content else ""
    
    # These were removed because they don't actually work on the deployed server
    # blog_post_path = os.path.join(settings.BASE_DIR, 'templates', 'blog', f'{template_name}.html')
    # created_timestamp = os.path.getctime(blog_post_path)
    # created_at = str(datetime.datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d'))
    # updated_timestamp = os.path.getmtime(blog_post_path)
    # updated_at = str(datetime.datetime.fromtimestamp(updated_timestamp).strftime('%Y-%m-%d'))
    
    # Adjust GitHub link to include category if present
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
        
        # "created_timestamp": created_timestamp,
        # "updated_timestamp": updated_timestamp,
        # "created_at": created_at,
        # "updated_at": updated_at,
    }

def find_blog_template(template_name):
    """Find a blog template by name, searching through all categories."""
    blog_templates_path = os.path.join(settings.BASE_DIR, 'templates', 'blog')
    
    # First check if it exists at the root level
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
    """Get all blog posts from all categories."""
    blog_posts = []
    blog_templates_path = os.path.join(settings.BASE_DIR, 'templates', 'blog')
    
    # Walk through all directories in the blog folder
    for root, dirs, files in os.walk(blog_templates_path):
        # Calculate the relative path from the blog directory
        rel_path = os.path.relpath(root, blog_templates_path)
        
        # Determine the category (if in a subdirectory)
        if rel_path == '.':
            category = None
        else:
            # Use the first directory level as the category
            category = rel_path.split(os.sep)[0]
        
        # Process HTML files
        for file in files:
            if file.endswith('.html'):
                template_name = file[:-5]  # Remove .html extension
                blog_posts.append({
                    'template_name': template_name,
                    'category': category,
                    'full_path': os.path.join(root, file)
                })
    
    return blog_posts
