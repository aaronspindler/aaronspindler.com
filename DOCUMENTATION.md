# aaronspindler.com - Complete Documentation

> *Comprehensive documentation for a Django-powered personal website with interactive knowledge graphs, smart photo management, and a template-based blog system*

## Table of Contents

1. [Project Overview](#project-overview)
   - [Key Features](#key-features)
   - [Tech Stack](#tech-stack)
2. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Local Development Setup](#local-development-setup)
   - [Docker Setup](#docker-setup)
3. [Development Guide](#development-guide)
   - [Common Development Commands](#common-development-commands)
   - [Architecture Overview](#architecture-overview)
   - [Django Apps Structure](#django-apps-structure)
4. [Testing](#testing)
   - [Test Data Factories](#test-data-factories)
   - [Docker Test Environment](#docker-test-environment)
   - [Running Tests](#running-tests)
5. [Key Features Documentation](#key-features-documentation)
   - [Knowledge Graph System](#knowledge-graph-system)
   - [Static File Optimization](#static-file-optimization)
   - [Blog Post System](#blog-post-system)
6. [Deployment](#deployment)
   - [Environment Variables](#environment-variables)
   - [Production Configuration](#production-configuration)
   - [Docker Deployment](#docker-deployment)
7. [API Reference](#api-reference)
8. [Maintenance](#maintenance)
9. [Contributing](#contributing)

---

## Project Overview

[![Django](https://img.shields.io/badge/Django-5.2.5-green?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)

This isn't your average personal website. It's a playground for web experiments and a showcase of what happens when you give Django some creative freedom.

### Key Features

- **Interactive Knowledge Graph** - Watch your blog posts connect in real-time with a D3.js-powered visualization that maps relationships between posts
- **Smart Photo Management** - Upload once, get 5 optimized sizes automatically, complete with EXIF data extraction
- **Template-Based Blog System** - No database clutter - blog posts live as HTML templates with rich metadata
- **Privacy-First Analytics** - Custom page visit tracking that respects user privacy
- **Server-Side Screenshots** - Playwright-powered screenshot generation for social media previews
- **Performance Optimized** - Static file compression, multi-stage Docker builds, and intelligent caching

### Tech Stack

- **Framework**: Django 5.2.5 with Python 3.13
- **Database**: PostgreSQL with psycopg3
- **Storage**: AWS S3 (optional) via django-storages
- **Authentication**: django-allauth for flexible auth options
- **Image Processing**: Pillow with automatic WebP generation
- **Screenshot Generation**: Playwright for server-side rendering
- **Task Queue**: Celery with Redis broker
- **Server**: Gunicorn with WhiteNoise for static files
- **Containerization**: Docker with health checks
- **Cache**: Redis for caching and sessions

---

## Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL 15+
- Node.js (for Playwright and asset building)
- Redis (for caching and Celery)
- Docker (optional, for containerized deployment)

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/aaronspindler/aaronspindler.com.git
cd aaronspindler.com

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright for screenshot generation
playwright install chromium

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser

# Collect and optimize static files
python manage.py collectstatic_optimize

# Run development server
python manage.py runserver
```

### Docker Setup

```bash
# Build and run with Docker Compose
docker-compose build
docker-compose up

# Or use the Makefile shortcuts
make build
make up
```

---

## Development Guide

*This section is from CLAUDE.md - guidance for AI assistants and developers*

### Common Development Commands

#### Local Development
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

#### Testing
```bash
# Run tests with parallel execution
python manage.py test --parallel

# Run tests with coverage
coverage run --source='.' manage.py test --no-input --parallel
coverage report

# Security check
safety check
```

#### CSS and JavaScript Build
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

#### Knowledge Graph Commands
```bash
# Rebuild knowledge graph cache
python manage.py rebuild_knowledge_graph

# Generate knowledge graph screenshot (high-quality)
python manage.py generate_knowledge_graph_screenshot \
    --width 2400 --height 1600 --device-scale-factor 2.0 \
    --quality 100 --transparent
```

#### Photo Management
```bash
# Generate photo album zips
python manage.py generate_album_zips
```

#### Cache Management
```bash
# Clear all caches
python manage.py clear_cache

# Setup periodic tasks (for Celery)
python manage.py setup_periodic_tasks
```

### Architecture Overview

#### Django Apps Structure

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

- **accounts/**: User authentication via django-allauth
  - Custom user model
  - Registration disabled by default (NoSignupAccountAdapter)

### Django Apps Structure

The project follows Django best practices with clear separation of concerns:

```
aaronspindler.com/
├── config/              # Main configuration
├── accounts/           # User authentication
├── blog/              # Blog and knowledge graph
├── pages/             # Core website pages
├── photos/            # Photo management
├── templates/         # Project templates
├── static/           # Static assets
└── tests/            # Test factories
```

---

## Testing

### Test Data Factories

*From tests/README.md*

This project uses a comprehensive factory system for test data that provides:
- **Consistent test data** across all apps
- **Reduced code duplication** in test files
- **Easy-to-use factory methods** for creating test objects
- **Flexible configuration** with sensible defaults

#### Quick Reference

```python
# Most commonly used factories
from tests.factories import (
    UserFactory,
    BlogCommentFactory,
    PageVisitFactory,
    PhotoFactory,
    MockDataFactory,
    TestDataMixin
)

# Create test users
user = UserFactory.create_user()
staff = UserFactory.create_staff_user()
admin = UserFactory.create_superuser()

# Create blog comments
comment = BlogCommentFactory.create_comment(author=user)
approved = BlogCommentFactory.create_approved_comment()

# Create page visits
visit = PageVisitFactory.create_visit()
geo_visit = PageVisitFactory.create_visit_with_geo()

# Create photos and albums
photo = PhotoFactory.create_photo()
album = PhotoFactory.create_photo_album()
```

#### Available Factories

##### UserFactory
```python
# Basic user
user = UserFactory.create_user()

# Custom user
user = UserFactory.create_user(username='customuser', email='custom@example.com')

# Staff user
staff = UserFactory.create_staff_user()

# Superuser
admin = UserFactory.create_superuser()

# Get common user data for forms
user_data = UserFactory.get_common_user_data()
```

##### BlogCommentFactory
```python
# Basic comment with user
comment = BlogCommentFactory.create_comment(author=user)

# Anonymous comment
comment = BlogCommentFactory.create_anonymous_comment()

# Approved comment
comment = BlogCommentFactory.create_approved_comment()

# Pending comment (default status)
comment = BlogCommentFactory.create_pending_comment()

# Nested comment (reply)
reply = BlogCommentFactory.create_comment(parent=comment)

# Comment vote
vote = BlogCommentFactory.create_comment_vote(comment, user, 'upvote')
```

##### PageVisitFactory
```python
# Basic visit
visit = PageVisitFactory.create_visit()

# Visit with geolocation
visit = PageVisitFactory.create_visit_with_geo()

# Custom visit
visit = PageVisitFactory.create_visit(
    ip_address='8.8.8.8',
    page_name='/custom-page/'
)

# Bulk visits
visits = PageVisitFactory.create_bulk_visits(count=50)
```

##### PhotoFactory
```python
# Basic photo with auto-generated test image
photo = PhotoFactory.create_photo()

# Photo with EXIF data
photo = PhotoFactory.create_photo_with_exif(
    camera_make='Canon',
    camera_model='EOS R5',
    iso=400,
    aperture='f/2.8',
    shutter_speed='1/250',
    focal_length='50mm'
)

# Photo album
album = PhotoFactory.create_photo_album(
    title='My Album',
    is_private=False,
    allow_downloads=True
)
```

### Docker Test Environment

*From DOCKER_TEST_README.md*

The test environment provides a complete production-like setup with:
- **PostgreSQL** database for testing
- **Redis** for caching and Celery message broker
- **LocalStack** for mocking AWS S3 services
- **Celery** workers and beat for background task testing

#### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Test Network                      │
├───────────────┬──────────────┬──────────────┬──────────────┤
│  LocalStack   │  PostgreSQL  │    Redis     │     Web      │
│   (S3 Mock)   │  (Database)  │  (Cache/MQ)  │   (Django)   │
│    :4566      │    :5433     │    :6380     │    :8001     │
└───────────────┴──────────────┴──────────────┴──────────────┘
                                       │
                          ┌────────────┴────────────┐
                          │                         │
                    Celery Worker            Celery Beat
                    (Async Tasks)           (Scheduler)
```

### Running Tests

#### Quick Start
```bash
# Run complete test suite
make test

# Run tests for a specific app
make test-run-app APP=blog

# Run specific test
make test-run-specific TEST=blog.tests.test_models.BlogCommentModelTest

# Run with coverage
make test-coverage
```

#### Managing Test Environment
```bash
# Start test environment in background
make test-up

# Stop test environment
make test-down

# View logs
make test-logs

# Open shell in test container
make test-shell
```

---

## Key Features Documentation

### Knowledge Graph System

Located in `blog/knowledge_graph.py`, the knowledge graph system:
- Builds interactive graph from blog post metadata
- Uses Playwright for server-side screenshot generation
- Implements caching system for performance
- LinkParser class for extracting internal/external links
- GraphBuilder for constructing graph structures

#### API Endpoints
- `/blog/knowledge-graph/data/` - Returns graph data as JSON
- `/blog/knowledge-graph/screenshot/` - Returns graph screenshot

#### Usage
```python
from blog.knowledge_graph import KnowledgeGraphBuilder

# Build graph from blog posts
builder = KnowledgeGraphBuilder()
graph_data = builder.build()
```

### Static File Optimization

Custom `collectstatic_optimize` command provides:
- Image compression with quality preservation
- CSS minification with PostCSS
- JavaScript minification with Terser
- Brotli compression for static assets
- WhiteNoise integration for serving

#### Commands
```bash
# Optimize and collect static files
python manage.py collectstatic_optimize

# Build CSS with critical extraction
python manage.py build_css

# Optimize JavaScript
python manage.py optimize_js
```

### Blog Post System

Blog posts are stored as HTML templates in `templates/blog/<category>/` with metadata:

```html
{% block meta_description %}Post description{% endblock %}
{% block meta_title %}Post Title{% endblock %}
{% block meta_publish_date %}YYYY-MM-DD{% endblock %}
{% block meta_post_type %}Category{% endblock %}
{% block meta_reading_time %}X{% endblock %}
```

Categories:
- `personal/` - Personal posts
- `projects/` - Project documentation
- `reviews/` - Product/service reviews
- `tech/` - Technical articles

---

## Deployment

### Environment Variables

Required environment variables (use django-environ):

```bash
# Core Settings
DATABASE_URL=postgresql://user:password@localhost/dbname
SECRET_KEY=your-secret-key
DEBUG=False

# AWS Settings (required)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_REGION_NAME=us-east-1  # optional

# Redis/Cache
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1  # defaults to REDIS_URL

# Optional Features
RESUME_ENABLED=True
RESUME_FILENAME=resume.pdf
```

### Production Configuration

#### Docker Deployment

The project includes multi-stage Docker builds for optimal size:

```dockerfile
# Build stage
FROM python:3.13-slim as builder
# ... dependency installation

# Runtime stage
FROM python:3.13-slim
# ... optimized runtime
```

Deploy with:
```bash
docker build -t aaronspindler .
docker run -p 8000:8000 --env-file .env aaronspindler
```

#### Health Checks

The application includes health check endpoints:
- `/health/` - Basic health check
- `/health/db/` - Database connectivity check
- `/health/cache/` - Cache connectivity check

#### Performance Optimizations

- Graph data caching with 20-minute timeout
- File modification time tracking for cache invalidation
- Multi-resolution image generation (thumbnail, small, medium, large)
- Static file compression and optimization
- Database query optimization with select/prefetch related

---

## API Reference

### Blog API Endpoints

#### Knowledge Graph Data
```
GET /blog/knowledge-graph/data/
```
Returns graph data with nodes and edges.

Response:
```json
{
  "nodes": [
    {
      "id": "post-slug",
      "label": "Post Title",
      "category": "tech",
      "date": "2024-01-01"
    }
  ],
  "edges": [
    {
      "source": "post-1",
      "target": "post-2",
      "type": "reference"
    }
  ]
}
```

#### Knowledge Graph Screenshot
```
GET /blog/knowledge-graph/screenshot/
```
Returns PNG image of the knowledge graph.

### Photo API Endpoints

#### Album Detail
```
GET /photos/album/<slug>/
```
Returns album details with photos.

#### Photo Download
```
GET /photos/album/<slug>/photo/<id>/download/
```
Downloads original photo file.

#### Album Download Status
```
GET /photos/album/<slug>/download/status/
```
Returns zip generation status.

---

## Maintenance

### Updating Dependencies

```bash
# Update Python packages
pip install --upgrade -r requirements.txt

# Update Node packages
npm update

# Rebuild Docker images
docker-compose build --no-cache
```

### Database Maintenance

```bash
# Backup database
python manage.py dumpdata > backup.json

# Restore database
python manage.py loaddata backup.json

# Clean old page visits
python manage.py shell
>>> from pages.models import PageVisit
>>> from datetime import datetime, timedelta
>>> old_date = datetime.now() - timedelta(days=90)
>>> PageVisit.objects.filter(created_at__lt=old_date).delete()
```

### Cache Management

```bash
# Clear all caches
python manage.py clear_cache

# Clear specific cache
from django.core.cache import cache
cache.delete_pattern('knowledge_graph:*')
```

### Performance Monitoring

Monitor key metrics:
- Database queries with django-debug-toolbar (development)
- Celery tasks with Flower dashboard
- Static file serving with WhiteNoise logs

### Request Fingerprinting

The application automatically tracks request fingerprints via `RequestFingerprintMiddleware`:

**Features:**
- Tracks IP address, user agent, browser, OS, device
- Generates unique fingerprints (with and without IP)
- Detects suspicious requests (bots, scanners, etc.)
- Associates with authenticated users
- Stores all relevant headers
- Skips static files and media to reduce database load

**Configuration:**

The middleware is enabled by default in `config/settings.py`. It automatically:
- Creates a `RequestFingerprint` record for each request
- Attaches the fingerprint to `request.fingerprint` for use in views
- Logs warnings for suspicious requests

**Querying fingerprints:**

```python
from utils.models import RequestFingerprint
from django.utils import timezone
from datetime import timedelta

# Get suspicious requests in last 24 hours
suspicious = RequestFingerprint.objects.filter(
    is_suspicious=True,
    created_at__gte=timezone.now() - timedelta(hours=24)
)

# Get all requests from a specific IP
ip_requests = RequestFingerprint.objects.filter(ip_address='192.168.1.1')

# Get user's request history
user_requests = RequestFingerprint.objects.filter(user=request.user)
```

**Accessing in views:**

```python
def my_view(request):
    # The middleware attaches the fingerprint to each request
    if hasattr(request, 'fingerprint'):
        fingerprint = request.fingerprint
        print(f"IP: {fingerprint.ip_address}")
        print(f"Browser: {fingerprint.browser}")
        if fingerprint.is_suspicious:
            # Handle suspicious request
            pass
```

---

## Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Write/update tests
5. Run test suite: `make test`
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push branch: `git push origin feature/amazing-feature`
8. Open Pull Request

### Code Standards

- Follow PEP 8 for Python code
- Use Black for code formatting
- Write comprehensive tests for new features
- Update documentation for API changes
- Add type hints where appropriate

### Testing Requirements

- All new features must have tests
- Use factories from `tests/factories.py`
- Maintain >80% code coverage
- Test both success and error cases

### Documentation

When adding new features:
1. Update this documentation
2. Add docstrings to new functions/classes
3. Update API reference if applicable
4. Include usage examples

### Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

---

## Important Notes

### Security Considerations

- Never commit secrets or API keys
- Use environment variables for sensitive data
- Implement rate limiting for public endpoints
- Keep dependencies updated for security patches

### Performance Tips

- Use select_related/prefetch_related for queries
- Implement caching for expensive operations
- Optimize images before upload
- Use database indexes for frequent queries

### Known Limitations

- Blog posts must be HTML templates (not database entries)
- Screenshot generation requires Playwright/Chromium
- Photo duplicate detection may have false positives
- Knowledge graph limited to ~100 posts for performance

---

## Support

For issues, questions, or contributions:
- GitHub Issues: [github.com/aaronspindler/aaronspindler.com/issues](https://github.com/aaronspindler/aaronspindler.com/issues)
- Documentation: This file
- Code Examples: See test files for usage patterns

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Acknowledgments

- Django community for the excellent framework
- Contributors and maintainers of all dependencies
- Open source community for inspiration and tools

---

*Last Updated: December 2024*