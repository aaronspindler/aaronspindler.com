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
# Run tests locally (without parallel execution)
python manage.py test

# Run tests with coverage locally (without parallel execution)
coverage run --source='.' manage.py test --no-input
coverage report

# Run tests in CI/CD with parallel execution
# Note: Only use --parallel flag in CI/CD environments, not locally
python manage.py test --parallel

# Security check
safety check
```

**IMPORTANT**: Do not write new tests for code in this repository unless explicitly requested.

### CSS and JavaScript Build
```bash
# Build and optimize CSS
npm run build:css

# Build critical CSS
npm run build:css:critical

# Build and minify JavaScript
npm run build:js

# Build all assets
npm run build:all
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
# Generate photo album zips
python manage.py generate_album_zips
```

### Lighthouse Performance Monitoring
```bash
# Run Lighthouse audit and store results
python manage.py run_lighthouse_audit

# Run audit for a specific URL
python manage.py run_lighthouse_audit --url https://example.com

# Setup daily automated audits (Celery Beat)
python manage.py setup_periodic_tasks
```

### Cache Management
```bash
# Clear all caches
python manage.py clear_cache

# Setup periodic tasks (for Celery)
python manage.py setup_periodic_tasks
```

## Architecture Overview

### Django Apps Structure
- **config/**: Main Django configuration
  - `settings.py`: Environment-based settings using django-environ
  - `urls.py`: Main URL routing
  - `storage_backends.py`: S3 storage configuration
  - `celery.py`: Celery configuration for async tasks

- **pages/**: Core website functionality
  - Page visit tracking with geo-location data
  - Custom decorators for visit tracking
  - Context processors for resume settings
  - Management commands for CSS/JS optimization

- **blog/**: Blog system with unique features
  - Template-based blog posts stored in `templates/blog/`
  - Knowledge graph visualization system
  - API endpoints for graph data and screenshots
  - Posts organized by category (personal, projects, reviews, tech)

- **photos/**: Photo management system
  - Photo model with automatic image optimization (multiple sizes)
  - EXIF metadata extraction
  - Album management with zip generation
  - Private/public album support

- **lighthouse_monitor/**: Performance monitoring system
  - Automated Lighthouse audits tracking all 5 metrics (Performance, Accessibility, Best Practices, SEO, PWA)
  - Historical performance data storage with 30-day visualization
  - Badge endpoint for shields.io integration
  - Celery Beat task for nightly audits at 2 AM UTC

- **accounts/**: User authentication via django-allauth
  - Custom user model
  - Registration disabled by default (NoSignupAccountAdapter)

### Key Technical Features

1. **Knowledge Graph System** (`blog/knowledge_graph.py`)
   - Builds interactive graph from blog post metadata
   - Uses Playwright for server-side screenshot generation
   - Caching system for performance
   - LinkParser class for extracting internal/external links
   - GraphBuilder for constructing graph structures

2. **Static File Optimization**
   - Custom `collectstatic_optimize` command with image compression
   - CSS build pipeline with PostCSS, PurgeCSS, and critical CSS extraction
   - JavaScript minification with Terser
   - Brotli compression for static assets
   - WhiteNoise for serving in production

3. **Blog Post System**
   - HTML templates as blog posts
   - Metadata extraction from templates
   - View count tracking per post
   - Category-based organization
   - Template normalization for consistency
   - **Important**: When modifying blog post templates in `templates/blog/*/*.html`, utilize existing stylesheets and maintain consistency with other posts

### Deployment Configuration
- **Docker**: Multi-stage build with Playwright for screenshot generation
- **Database**: PostgreSQL with psycopg3
- **Storage**: AWS S3 support via django-storages
- **Server**: Gunicorn with 8 workers
- **Cache**: Redis for caching and sessions
- **Task Queue**: Celery with Redis broker

### Environment Variables
Required environment variables (use django-environ):
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode flag
- AWS credentials (required for production with S3 storage; optional for local development):
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_STORAGE_BUCKET_NAME`
  - `AWS_S3_REGION_NAME` (optional, defaults to us-east-1)
- `REDIS_URL`: Redis connection URL (for caching)
- `CELERY_BROKER_URL`: Celery broker URL (defaults to REDIS_URL)
- `RESUME_ENABLED`: Enable resume download feature
- `RESUME_FILENAME`: Resume file name

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
- Parallel test execution supported (CI/CD only, not for local development)
- Test files organized in app-specific `tests/` directories
- Coverage reporting with coverage.py
- CI/CD via GitHub Actions with PostgreSQL service container

### Performance Optimizations
- Graph data caching with 20-minute timeout
- File modification time tracking for cache invalidation
- Multi-resolution image generation (thumbnail, small, medium, large)
- Static file compression and optimization
- Database query optimization with select/prefetch related