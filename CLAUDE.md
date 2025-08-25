# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based personal website and blog (aaronspindler.com) with advanced features including knowledge graph visualization, photo management, and analytics tracking.

## Common Development Commands

### Local Development
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files (with optimization)
python manage.py collectstatic_optimize

# Run development server
python manage.py runserver

# Create superuser for admin access
python manage.py createsuperuser
```

### Testing
```bash
# Run tests with parallel execution
python manage.py test --parallel

# Run tests with coverage
coverage run --source='.' manage.py test --no-input --parallel
coverage report

# Security check
safety check
```

### Knowledge Graph Commands
```bash
# Rebuild knowledge graph cache
python manage.py rebuild_knowledge_graph

# Generate knowledge graph screenshot (high-quality)
python manage.py generate_knowledge_graph_screenshot --width 2400 --height 1600 --device-scale-factor 2.0 --quality 100 --transparent
```

### Photo Management
```bash
# Extract EXIF data from photos
python manage.py extract_exif_data
```

## Architecture Overview

### Django Apps Structure
- **config/**: Main Django configuration
  - `settings.py`: Environment-based settings using django-environ
  - `urls.py`: Main URL routing
  - `storage_backends.py`: S3 storage configuration

- **pages/**: Core website functionality
  - Page visit tracking with geo-location data
  - Photo model with automatic image optimization (multiple sizes)
  - EXIF metadata extraction
  - Custom decorators for visit tracking

- **blog/**: Blog system with unique features
  - Template-based blog posts stored in `templates/blog/`
  - Knowledge graph visualization system
  - API endpoints for graph data and screenshots
  - Posts organized by category (personal, projects, reviews, tech)

- **accounts/**: User authentication via django-allauth

### Key Technical Features

1. **Knowledge Graph System** (`blog/knowledge_graph.py`)
   - Builds interactive graph from blog post metadata
   - Uses Playwright for server-side screenshot generation
   - Caching system for performance

2. **Image Optimization** (`pages/image_utils.py`)
   - Automatic multi-resolution image generation (thumbnail, small, medium, large)
   - EXIF data extraction and storage
   - WebP format support

3. **Static File Optimization**
   - Custom `collectstatic_optimize` command
   - Gzip compression for static assets
   - WhiteNoise for serving in production

4. **Blog Post System**
   - HTML templates as blog posts
   - Metadata extraction from templates
   - View count tracking per post
   - Category-based organization

### Deployment Configuration
- **Docker**: Multi-stage build with Playwright for screenshot generation
- **Database**: PostgreSQL with psycopg3
- **Storage**: AWS S3 support via django-storages
- **Server**: Gunicorn with 5 workers
- **Health checks**: Built-in Docker health check endpoint

### Environment Variables
Required environment variables (use django-environ):
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode flag
- `USE_S3`: Enable S3 storage (optional)
- AWS credentials if using S3

### Blog Post Template Structure
Blog posts are HTML templates in `templates/blog/<category>/<filename>.html` with metadata:
```html
{% block meta_description %}Post description{% endblock %}
{% block meta_title %}Post Title{% endblock %}
{% block meta_publish_date %}YYYY-MM-DD{% endblock %}
{% block meta_post_type %}Category{% endblock %}
{% block meta_reading_time %}X{% endblock %}
```

### Testing Approach
- Django's built-in test framework
- Parallel test execution supported
- Coverage reporting with coverage.py
- CI/CD via GitHub Actions with PostgreSQL service container