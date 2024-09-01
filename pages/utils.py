import datetime
import os
from django.conf import settings
from django.template.loader import render_to_string

def get_blog_from_template_name(template_name):
    blog_post_path = os.path.join(settings.BASE_DIR, 'templates', 'blog', f'{template_name}.html')
    created_timestamp = os.path.getctime(blog_post_path)
    created_at = str(datetime.datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d'))
    updated_timestamp = os.path.getmtime(blog_post_path)
    updated_at = str(datetime.datetime.fromtimestamp(updated_timestamp).strftime('%Y-%m-%d'))
    blog_title = template_name.replace("_", " ").title()
    blog_content = render_to_string(f"blog/{template_name}.html")
    
    return {
        "created_timestamp": created_timestamp,
        "updated_timestamp": updated_timestamp,
        "created_at": created_at,
        "updated_at": updated_at,
        "blog_title": blog_title,
        "blog_content": blog_content,
        "template_name": template_name,
    }