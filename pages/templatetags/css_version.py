from django import template
from django.conf import settings
from pathlib import Path
import os

register = template.Library()

@register.simple_tag
def versioned_css():
    """Return the path to the latest versioned CSS file"""
    try:
        static_dir = os.path.join(settings.BASE_DIR, 'static', 'css')
        
        # Find the most recent combined.min.*.css file
        css_files = list(Path(static_dir).glob('combined.min.*.css'))
        
        if css_files:
            # Sort by modification time and get the most recent
            latest_file = max(css_files, key=lambda f: f.stat().st_mtime)
            # Return just the filename for use with {% static %}
            return f'css/{latest_file.name}'
    except Exception:
        # Handle any errors (missing directory, glob issues, etc.)
        pass
    
    # Fallback to non-versioned file
    return 'css/combined.min.css'