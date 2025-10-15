# aaronspindler.com

> *A Django-powered personal website with a twist - featuring interactive knowledge graphs, smart photo management, and a blog system that thinks outside the database*

## Table of Contents

- [What Makes This Site Special](#what-makes-this-site-special)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Architecture & Structure](#architecture--structure)
- [Creating Blog Posts](#creating-blog-posts)
- [Knowledge Graph](#knowledge-graph)
- [Photo Management](#photo-management)
- [Testing](#testing)
- [Performance Features](#performance-features)
- [Management Commands](#management-commands)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Maintenance](#maintenance)
- [Contributing](#contributing)
- [Additional Information](#additional-information)

[![Django](https://img.shields.io/badge/Django-5.2.5-green?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)

## What Makes This Site Special

This isn't your average personal website. It's a playground for web experiments and a showcase of what happens when you give Django some creative freedom.

### Key Features

- **= Interactive Knowledge Graph** - Watch your blog posts connect in real-time with a D3.js-powered visualization that maps relationships between posts (now with enhanced stability for large graphs)
- **= Smart Photo Management** - Upload once, get 5 optimized sizes automatically, complete with EXIF data extraction
- **= Template-Based Blog System** - No database clutter - blog posts live as HTML templates with rich metadata
- **= Full-Text Search** - PostgreSQL-powered search with typo tolerance using trigram similarity, autocomplete after 2 characters, sub-100ms response time
- **= Automated Performance Monitoring** - Nightly Lighthouse audits tracking 4 key metrics with historical trends and badge display
- **= Privacy-First Analytics** - Custom page visit tracking that respects user privacy
- **< Server-Side Screenshots** - Playwright-powered screenshot generation for social media previews
- ** Performance Optimized** - Static file compression, multi-stage Docker builds, and intelligent caching

## Tech Stack

- **Framework**: Django 5.2.5 with Python 3.13
- **Database**: PostgreSQL with psycopg3 + full-text search (pg_trgm, unaccent extensions)
- **Storage**: AWS S3 (optional) via django-storages
- **Authentication**: django-allauth for flexible auth options
- **Image Processing**: Pillow with automatic WebP generation
- **Screenshot Generation**: Playwright for server-side rendering
- **Search**: PostgreSQL FTS with trigram similarity for typo tolerance
- **Server**: Gunicorn with WhiteNoise for static files
- **Containerization**: Docker with health checks

## Architecture & Structure

### Project Structure

```
aaronspindler.com/
├── config/              # Main Django configuration
│   ├── settings.py     # Environment-based settings
│   ├── urls.py         # Main URL routing
│   ├── storage_backends.py  # S3 storage configuration
│   └── celery.py       # Celery async task configuration
├── accounts/           # User authentication
│   ├── models.py       # Custom user model
│   └── adapters.py     # django-allauth customization
├── blog/              # Blog system and knowledge graph
│   ├── models.py       # Blog comments, votes, screenshots
│   ├── views.py        # Blog rendering, comments, voting
│   ├── knowledge_graph.py  # Graph building and visualization
│   ├── utils.py        # Blog template utilities
│   ├── forms.py        # Comment forms
│   └── templates/blog/ # Blog post templates by category
├── pages/             # Core website pages
│   ├── views.py        # Home, health check, resume
│   ├── utils.py        # Books and projects data
│   └── management/     # CSS/JS optimization commands
├── photos/            # Photo management
│   ├── models.py       # Photo and PhotoAlbum models
│   ├── image_utils.py  # EXIF extraction, optimization
│   └── tasks.py        # Album zip generation (Celery)
├── utils/             # Cross-cutting utilities
│   ├── models/         # Utility models (search, notifications, security)
│   ├── search.py       # Full-text search functions
│   ├── middleware.py   # Request fingerprinting
│   ├── tasks.py        # Notification tasks
│   └── management/     # Search index, cache commands
├── templates/         # Project-wide templates
├── static/           # Static assets (CSS, JS, images)
└── tests/            # Test data factories
```

### Django Apps Overview

**config/** - Main Configuration
- Environment-based settings using django-environ
- URL routing and middleware configuration
- S3 storage backends for media/static files
- Celery configuration for async tasks

**accounts/** - User Authentication
- Custom user model extending AbstractUser
- Registration disabled by default (NoSignupAccountAdapter)
- Integration with django-allauth

**blog/** - Blog System & Knowledge Graph
- Template-based blog posts in `templates/blog/<category>/`
- Knowledge graph visualization with D3.js
- Blog comments with moderation and voting
- API endpoints for graph data and screenshots
- Categories: personal, projects, reviews, tech

**pages/** - Core Website
- Home page with blog posts, projects, books, albums
- Page visit tracking with request fingerprinting
- Resume download functionality
- Context processors for global template data
- Management commands for static file optimization

**photos/** - Photo Management
- Photo model with automatic multi-size optimization
- EXIF metadata extraction (camera, lens, GPS, etc.)
- PhotoAlbum model with zip file generation
- Private/public album support
- Duplicate detection using perceptual hashing

**utils/** - Shared Utilities
- **Search**: PostgreSQL full-text search with SearchableContent model
- **Notifications**: Email and SMS notification system
- **Security**: Request fingerprinting and tracking
- **Lighthouse**: Performance monitoring and audits
- **Middleware**: Request fingerprinting for analytics
- **Management Commands**: Search index, cache management

## Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL 15+
- Node.js (for Playwright)

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/aaronspindler/aaronspindler.com.git
cd aaronspindler.com

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development tools (linting, type checking, pre-commit)

# Install Playwright browsers
playwright install chromium

# Set up environment variables
cp .env.example .env  # Edit with your settings

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Set up Git hooks (auto-linting on commit/push)
./scripts/setup-git-hooks.sh

# Collect and optimize static files
python manage.py collectstatic_optimize

# Build search index
python manage.py rebuild_search_index

# Fire it up!
python manage.py runserver
```

Visit `http://localhost:8000` and enjoy! <

### Docker Setup

```bash
# Build the image
docker build -t aaronspindler.com .

# Run with environment variables
docker run -p 80:80 \
  -e DATABASE_URL="postgres://user:pass@host/db" \
  -e SECRET_KEY="your-secret-key" \
  -e DEBUG=False \
  aaronspindler.com
```

## Creating Blog Posts

Blog posts are HTML templates - no admin panel needed! You can create them manually or use the management command:

### Using the Management Command (Recommended)

```bash
# Create a new blog post with automatic numbering
python manage.py create_blog_post --title "Your Blog Title" --category tech

# Available categories: personal, projects, reviews, tech
python manage.py create_blog_post --title "Weekend Adventures" --category personal
```

The command will:
- Automatically assign the next available blog number
- Create the file in the correct category directory
- Generate a template with examples and formatting guidelines

### Manual Creation

1. Add your template to `blog/templates/blog/<category>/####_Post_Name.html`
2. Write your content using HTML
3. Rebuild the knowledge graph to include the new post:

```bash
python manage.py rebuild_knowledge_graph
```

## Knowledge Graph

The knowledge graph automatically visualizes relationships between your blog posts with enhanced stability for large networks:

```bash
# Generate a high-quality screenshot of your knowledge graph
python manage.py generate_knowledge_graph_screenshot \
  --width 2400 \
  --height 1600 \
  --quality 100 \
  --transparent
```

## Photo Management

Upload photos through the admin panel and get:
- = **5 optimized sizes** (thumbnail, small, medium, large, original)
- = **EXIF data extraction** (camera, lens, GPS coordinates)
- = **Automatic WebP conversion** for modern browsers
- = **S3 storage support** for production

## Testing

### Quick Start

```bash
# Run the test suite with parallel execution
python manage.py test --parallel

# With coverage reporting
coverage run --source='.' manage.py test --no-input --parallel
coverage report
coverage html  # Open htmlcov/index.html for detailed report

# Security audit
safety check
```

### Test Data Factories

This project uses a comprehensive factory system for consistent test data across all apps.

#### Quick Reference

```python
from tests.factories import (
    UserFactory,
    BlogCommentFactory,
    PageVisitFactory,
    PhotoFactory,
    TestDataMixin
)

# Create test users
user = UserFactory.create_user()
staff = UserFactory.create_staff_user()
admin = UserFactory.create_superuser()

# Create blog comments
comment = BlogCommentFactory.create_comment(author=user)
approved = BlogCommentFactory.create_approved_comment()
reply = BlogCommentFactory.create_comment(parent=comment)

# Create page visits
visit = PageVisitFactory.create_visit()
geo_visit = PageVisitFactory.create_visit_with_geo()

# Create photos
photo = PhotoFactory.create_photo()
album = PhotoFactory.create_photo_album()
```

#### Available Factories

**UserFactory** - Create test users with various permission levels
```python
user = UserFactory.create_user()
user = UserFactory.create_user(username='custom', email='custom@example.com')
staff = UserFactory.create_staff_user()
admin = UserFactory.create_superuser()
```

**BlogCommentFactory** - Create blog comments and votes
```python
comment = BlogCommentFactory.create_comment(author=user)
anonymous = BlogCommentFactory.create_anonymous_comment()
approved = BlogCommentFactory.create_approved_comment()
vote = BlogCommentFactory.create_comment_vote(comment, user, 'upvote')
```

**PageVisitFactory** - Create page visit tracking data
```python
visit = PageVisitFactory.create_visit()
geo_visit = PageVisitFactory.create_visit_with_geo()
visits = PageVisitFactory.create_bulk_visits(count=50)
```

**PhotoFactory** - Create photos with auto-generated test images
```python
photo = PhotoFactory.create_photo()
photo = PhotoFactory.create_photo_with_exif(
    camera_make='Canon',
    camera_model='EOS R5',
    iso=400
)
album = PhotoFactory.create_photo_album(title='My Album')
```

### Docker Test Environment

The project includes an optimized test environment with Docker Compose:

```
┌────────────────────────────────────────────────────────┐
│           Docker Test Network (Optimized)              │
├──────────────┬──────────────┬──────────────────────────┤
│  PostgreSQL  │    Redis     │      Test Runner         │
│  (Database)  │  (Cache/MQ)  │  (Django + Playwright)   │
│    :5433     │    :6380     │        :8001             │
└──────────────┴──────────────┴──────────────────────────┘
```

**Optimizations:**
- ✅ Uses FileSystemStorage (no S3 mocking = 60-90% faster)
- ✅ No external AWS services needed
- ✅ Simple 2-service setup (just postgres + redis)
- ✅ Faster startup (~10s vs ~40s with LocalStack)

**Running Tests with Docker:**

```bash
# Run complete test suite (fast - uses FileSystemStorage)
make test

# Run tests for specific app
make test-run-app APP=blog

# Run specific test class
make test-run-specific TEST=blog.tests.test_models.BlogCommentModelTest

# Run with coverage
make test-coverage

# Manage test environment
make test-up      # Start test services (postgres + redis only)
make test-down    # Stop test services
make test-logs    # View logs
make test-shell   # Open Django shell in test container
```

See `TESTING_OPTIMIZATION.md` for detailed performance comparison and optimization strategies.

## Performance Features

- **Lighthouse Monitoring**: Automated nightly audits tracking Performance, Accessibility, Best Practices, and SEO scores with 30-day history visualization
- **Full-Text Search**: PostgreSQL-powered search with GIN indexes and trigram similarity for sub-100ms autocomplete queries
- **Static File Optimization**: Custom management command for gzipping assets
- **Intelligent Caching**: Knowledge graph caching with smart invalidation
- **Image Lazy Loading**: Automatic srcset generation for responsive images
- **Database Query Optimization**: Select/prefetch related for efficient queries

## Management Commands

This project includes several custom management commands for various operations:

### Blog Management

**create_blog_post** - Create a new blog post with automatic numbering
```bash
python manage.py create_blog_post --title "Your Post Title" --category tech
```
Options:
- `--title` (required): Title of the blog post
- `--category` (required): Category (personal, projects, reviews, tech)

**rebuild_knowledge_graph** - Rebuild the knowledge graph cache
```bash
python manage.py rebuild_knowledge_graph
python manage.py rebuild_knowledge_graph --force  # Force rebuild even if no changes detected
python manage.py rebuild_knowledge_graph --test-api  # Test the API endpoint after rebuild
```

**generate_knowledge_graph_screenshot** - Generate high-quality knowledge graph screenshots
```bash
python manage.py generate_knowledge_graph_screenshot --width 2400 --height 1600 --device-scale-factor 2.0 --quality 100 --transparent
```
Options:
- `--width`: Screenshot width in pixels (default: 1920)
- `--height`: Screenshot height in pixels (default: 1080)
- `--device-scale-factor`: Device pixel ratio for high-DPI displays (default: 2.0)
- `--quality`: JPEG quality 1-100 (default: 90)
- `--transparent`: Use transparent background

### Static File Optimization

**collectstatic_optimize** - Collect static files with image optimization
```bash
python manage.py collectstatic_optimize
```
Automatically optimizes images and creates compressed versions during collection.

**build_css** - Build and optimize CSS with advanced minification
```bash
python manage.py build_css  # Production mode with full optimization
python manage.py build_css --dev  # Development mode (skip purging, keep source maps)
```
Features:
- Combines and minifies CSS files
- Runs PostCSS with advanced configuration
- Purges unused CSS (production mode)
- Creates gzip and brotli compressed versions
- Generates versioned filenames with hash

**optimize_js** - Optimize JavaScript files
```bash
python manage.py optimize_js
python manage.py optimize_js --skip-minify  # Skip minification
python manage.py optimize_js --skip-compress  # Skip compression
```

**clear_cache** - Clear all cache keys from Redis
```bash
python manage.py clear_cache
```

### Photo Management

**generate_album_zips** - Generate zip files for photo albums
```bash
python manage.py generate_album_zips --all  # Generate for all albums with downloads enabled
python manage.py generate_album_zips --album-id 1  # Generate for specific album by ID
python manage.py generate_album_zips --album-slug "my-album"  # Generate for specific album by slug
python manage.py generate_album_zips --album-id 1 --async  # Use Celery for async processing
```

### Search Index Management

**rebuild_search_index** - Rebuild PostgreSQL full-text search index
```bash
python manage.py rebuild_search_index  # Rebuild all content types
python manage.py rebuild_search_index --clear  # Clear and rebuild entire index
python manage.py rebuild_search_index --content-type blog  # Rebuild only blog posts
python manage.py rebuild_search_index --content-type photos  # Rebuild only photos
python manage.py rebuild_search_index --content-type albums  # Rebuild only photo albums
python manage.py rebuild_search_index --content-type books  # Rebuild only books
python manage.py rebuild_search_index --content-type projects  # Rebuild only projects
```

Options:
- `--clear`: Clear existing search index before rebuilding
- `--content-type`: Rebuild specific content type (blog, photos, albums, books, projects, all)

Features:
- Indexes blog posts from templates with full content
- Indexes photos and albums with search vectors
- Indexes books and projects from utility functions
- Updates PostgreSQL search vectors with weighted fields (title: A, description: B, content: C)
- Provides progress feedback and statistics

**Note**: Run this command after:
- Adding new blog posts
- Modifying blog post content
- Adding new photos/albums
- Updating project or book data

### Performance Monitoring

**run_lighthouse_audit** - Run Lighthouse performance audit
```bash
python manage.py run_lighthouse_audit
python manage.py run_lighthouse_audit --url https://example.com  # Audit a specific URL
```
Tracks Performance, Accessibility, Best Practices, and SEO scores with historical data storage.

**setup_periodic_tasks** - Configure Celery Beat periodic tasks
```bash
python manage.py setup_periodic_tasks
```
Sets up automated tasks:
- Daily Lighthouse audit at 2 AM UTC
- Daily sitemap rebuild at 3 AM UTC
- Daily knowledge graph screenshot at 4 AM UTC
- Knowledge graph cache rebuild every 6 hours

### Security & Request Tracking

**geolocate_fingerprints** - Geolocate IP addresses for request fingerprints
```bash
python manage.py geolocate_fingerprints  # Process all records without geo data
python manage.py geolocate_fingerprints --limit 100  # Limit to 100 records
python manage.py geolocate_fingerprints --force  # Re-geolocate all records
python manage.py geolocate_fingerprints --batch-size 50  # Custom batch size
```

Features:
- Batch processes IP addresses using ip-api.com (free tier)
- Automatically filters local/private IPs (127.0.0.1, 10.x.x.x, etc.)
- Stores city, country, coordinates, timezone, ISP, and organization
- Respects API rate limits (15 requests/minute for batches, 100 IPs per batch)
- Updates all records sharing the same IP address

**Note**: Geolocation is NOT performed during request processing to avoid adding latency to responses. Run this command periodically (e.g., via cron or Celery Beat) to batch process new requests.

### Common Workflows

**Complete build pipeline for production:**
```bash
python manage.py build_css  # Build and optimize CSS
python manage.py optimize_js  # Optimize JavaScript
python manage.py collectstatic_optimize  # Collect and optimize static files
python manage.py rebuild_knowledge_graph  # Rebuild knowledge graph
python manage.py generate_knowledge_graph_screenshot --width 2400 --height 1600 --quality 100
python manage.py rebuild_search_index  # Rebuild search index
```

**Development workflow:**
```bash
python manage.py build_css --dev  # Development mode CSS build
python manage.py runserver  # Start development server
```

**Pre-commit hooks (Code Quality):**
```bash
# Run all hooks manually
pre-commit run --all-files

# Run specific hook
pre-commit run ruff

# Update hooks to latest versions
pre-commit autoupdate

# Skip hooks if needed (not recommended)
git commit --no-verify
```

Simplified pre-commit setup (all-in-one with Ruff):
- **Ruff linter:** Python linting with auto-fix
- **Ruff formatter:** Code formatting (Black-compatible)
- **Ruff import sorting:** Organize imports automatically
- **File checks:** Trailing whitespace, end-of-file, YAML validation

Heavier checks (MyPy, Django checks) stay in CI/CD only to keep commits fast.

---

## API Reference

### Knowledge Graph API

#### Get Graph Data
```
GET /api/knowledge-graph/
POST /api/knowledge-graph/
```

**Query Parameters (GET):**
- `post` - Get graph for specific post
- `depth` - Depth of connections (default: 1)
- `refresh` - Force refresh cache (true/false)

**POST Operations:**
```json
{
  "operation": "full_graph" | "refresh" | "post_graph",
  "template_name": "post_name",
  "depth": 1
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "nodes": [
      {
        "id": "post-slug",
        "label": "Post Title",
        "category": "tech",
        "url": "/b/tech/post-slug/"
      }
    ],
    "edges": [
      {
        "source": "post-1",
        "target": "post-2",
        "type": "internal"
      }
    ]
  },
  "metadata": {
    "nodes_count": 10,
    "edges_count": 15,
    "has_errors": false
  }
}
```

#### Get Graph Screenshot
```
GET /api/knowledge-graph/screenshot/
```

**Response:** PNG image of the knowledge graph

### Search API

#### Autocomplete
```
GET /api/search/autocomplete/?q=<query>
```

**Query Parameters:**
- `q` - Search query (minimum 2 characters)

**Response:**
```json
{
  "suggestions": [
    {
      "title": "Django Tutorial",
      "type": "Blog Post",
      "url": "/b/tech/django-tutorial/",
      "category": "tech"
    },
    {
      "title": "My Project",
      "type": "Project",
      "url": "https://github.com/user/project",
      "external": true
    }
  ]
}
```

### Lighthouse API

#### Badge Endpoint
```
GET /api/lighthouse/badge/
```

**Response (shields.io format):**
```json
{
  "schemaVersion": 1,
  "label": "lighthouse",
  "message": "95/98/100/100",
  "color": "brightgreen"
}
```

### Photo API

#### Album Detail
```
GET /photos/album/<slug>/
```

Returns album details with photos.

#### Album Download Status
```
GET /photos/album/<slug>/download/status/
```

Returns zip generation status for downloadable albums.

---

## Deployment

### Environment Variables

Required environment variables for production deployment:

```bash
# Core Django Settings
SECRET_KEY=your-long-random-secret-key
DEBUG=False
DATABASE_URL=postgresql://user:password@host:5432/dbname

# AWS S3 Storage (Required for production)
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1  # Optional, defaults to us-east-1

# Redis & Caching
REDIS_URL=redis://localhost:6379/0
USE_DEV_CACHE_PREFIX=False  # Set to True for local development

# Celery (defaults to REDIS_URL if not set)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Optional Features
RESUME_ENABLED=True
RESUME_FILENAME=Your_Resume_2025.pdf
```

### Production Configuration

#### Docker Deployment

The project uses multi-stage Docker builds for optimized production images:

```bash
# Build production image
docker build -t aaronspindler.com .

# Run with environment file
docker run -p 80:80 --env-file .env.production aaronspindler.com

# Or use Docker Compose
docker-compose -f docker-compose.production.yml up -d
```

#### Health Checks

The application includes health check endpoints for monitoring:

- **`/health/`** - Basic application health
- **Database check** - Verifies PostgreSQL connectivity
- **Cache check** - Verifies Redis connectivity (non-critical)

**Health Check Response:**
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "cache": "ok"
  }
}
```

#### Performance Optimizations

The application includes several production optimizations:

- **Caching**: Redis-backed caching for expensive operations
  - Graph data cache: 20-minute timeout
  - Blog posts cache: 1-hour timeout
  - Projects/books cache: 24-hour timeout

- **Static Files**:
  - Brotli and gzip compression
  - WhiteNoise for efficient serving
  - Hashed filenames for cache busting

- **Database**:
  - Connection pooling
  - Query optimization with select/prefetch_related
  - GIN indexes for full-text search

- **Images**:
  - Multi-resolution generation
  - WebP conversion for modern browsers
  - Lazy loading implementation

#### Security Headers

Production deployment includes security headers:
- SSL redirect enabled
- HSTS with 1-year max-age
- Content Security Policy (CSP)
- XSS protection
- Clickjacking protection

---

## Maintenance

### Updating Dependencies

```bash
# Update Python packages
pip install --upgrade -r requirements.txt

# Update development dependencies
pip install --upgrade -r requirements-dev.txt

# Update Node packages
npm update

# Rebuild Docker images after updates
docker-compose build --no-cache
```

### Database Maintenance

#### Backup Database

```bash
# Export all data to JSON
python manage.py dumpdata > backup.json

# Export specific app
python manage.py dumpdata blog > blog_backup.json

# Export without contenttypes (for faster restore)
python manage.py dumpdata --exclude contenttypes --exclude auth.permission > backup.json
```

#### Restore Database

```bash
# Restore from backup
python manage.py loaddata backup.json
```

#### Clean Old Data

```python
# Clean old page visits (90+ days)
python manage.py shell

from pages.models import PageVisit
from datetime import datetime, timedelta

old_date = datetime.now() - timedelta(days=90)
deleted = PageVisit.objects.filter(created_at__lt=old_date).delete()
print(f"Deleted {deleted[0]} old page visits")
```

### Cache Management

```bash
# Clear all caches
python manage.py clear_cache

# Clear specific cache pattern (in Django shell)
from django.core.cache import cache
cache.delete_pattern('knowledge_graph:*')
cache.delete_pattern('home_*')
```

### Request Fingerprinting

The application automatically tracks request fingerprints via `RequestFingerprintMiddleware`.

**Features:**
- Tracks IP address, user agent, browser, OS, device
- Generates unique fingerprints (with and without IP)
- Detects suspicious requests (bots, scanners)
- Associates with authenticated users
- IP geolocation support (batch processed via management command)
- Skips static files and media

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

# Get all requests from specific IP
ip_requests = RequestFingerprint.objects.filter(ip_address='192.168.1.1')

# Get user's request history
user_requests = RequestFingerprint.objects.filter(user=request.user)

# Get geolocated requests from specific country
us_requests = RequestFingerprint.objects.filter(geo_data__country='United States')

# Get requests from specific city
nyc_requests = RequestFingerprint.objects.filter(geo_data__city='New York')
```

**Accessing in views:**

```python
def my_view(request):
    if hasattr(request, 'fingerprint'):
        fingerprint = request.fingerprint
        print(f"IP: {fingerprint.ip_address}")
        print(f"Browser: {fingerprint.browser}")

        # Access geolocation data (if available)
        if fingerprint.geo_data:
            print(f"Location: {fingerprint.geo_data.get('city')}, {fingerprint.geo_data.get('country')}")
            print(f"Coordinates: {fingerprint.geo_data.get('lat')}, {fingerprint.geo_data.get('lon')}")
            print(f"ISP: {fingerprint.geo_data.get('isp')}")

        if fingerprint.is_suspicious:
            # Handle suspicious request
            pass
```

**Geolocation workflow:**

```bash
# 1. Requests are tracked automatically (geo_data is initially null)
# 2. Periodically run the geolocation command (e.g., via cron or Celery Beat)
python manage.py geolocate_fingerprints

# 3. Query geolocated data as shown above
```

### Monitoring

**Performance Monitoring:**
- Lighthouse audits run nightly at 2 AM UTC
- View history at `/lighthouse/history/`
- Badge endpoint: `/api/lighthouse/badge/`

**Celery Monitoring:**
```bash
# Monitor Celery tasks with Flower
celery -A config flower

# View at http://localhost:5555
```

---

## Contributing

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Write/update tests** - All features require tests
5. **Run the test suite**
   ```bash
   make test  # or python manage.py test
   ```
6. **Commit your changes**
   ```bash
   git commit -m 'feat: Add amazing feature'
   ```
7. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```
8. **Open a Pull Request**

### Code Standards

- **Python**: Follow PEP 8 style guide
- **Formatting**: Use Ruff (Black-compatible) for code formatting
- **Type Hints**: Add type hints for function parameters and return values
- **Docstrings**: Document all public functions, classes, and methods
- **Pre-commit**: Run `pre-commit run --all-files` before committing

### Testing Requirements

- All new features **must** have comprehensive tests
- Use factories from `tests/factories.py` for test data
- Maintain test coverage above 80%
- Test both success and error cases
- Write integration tests for complex workflows

### Commit Message Convention

Follow conventional commits format:

- **`feat:`** New feature
- **`fix:`** Bug fix
- **`docs:`** Documentation changes
- **`style:`** Code style changes (formatting, etc.)
- **`refactor:`** Code refactoring without behavior change
- **`test:`** Test additions or changes
- **`chore:`** Maintenance tasks, dependency updates

**Examples:**
```bash
git commit -m "feat: Add full-text search with autocomplete"
git commit -m "fix: Resolve knowledge graph rendering bug"
git commit -m "docs: Update API reference with new endpoints"
```

### Documentation Updates

When adding new features, update:
1. **README.md** - User-facing documentation
2. **CLAUDE.md** - AI assistant guidance
3. **Docstrings** - In-code documentation
4. **API Reference** - If adding new endpoints

### Pull Request Guidelines

- Provide clear description of changes
- Link related issues
- Include screenshots/videos for UI changes
- Ensure all CI/CD checks pass
- Respond to review feedback promptly

---

## Additional Information

### Security Considerations

**Important Security Practices:**

- **Secrets Management**: Never commit secrets or API keys to the repository
  - Use environment variables for all sensitive data
  - Add sensitive files to `.gitignore`
  - Rotate keys if accidentally committed

- **Rate Limiting**: Implement rate limiting for public API endpoints
  - Use Django middleware or third-party packages
  - Monitor for abuse patterns

- **Dependency Updates**: Keep dependencies current for security patches
  ```bash
  pip install --upgrade -r requirements.txt
  safety check  # Scan for known vulnerabilities
  ```

- **Input Validation**: Always validate user input
  - Use Django forms for validation
  - Sanitize HTML content
  - Implement CSRF protection (enabled by default)

- **Request Fingerprinting**: Monitor suspicious requests
  ```python
  # View suspicious requests
  RequestFingerprint.objects.filter(is_suspicious=True)
  ```

### Known Limitations

- **Blog Posts**: Must be HTML templates (not database entries)
  - Requires file system access to add new posts
  - Templates must follow naming convention
  - No built-in web editor

- **Screenshot Generation**: Requires Playwright/Chromium
  - Increases Docker image size
  - Memory-intensive operation
  - Not suitable for serverless deployments

- **Photo Duplicate Detection**: May have false positives
  - Uses perceptual hashing which is similarity-based
  - Very similar but different photos may be flagged
  - Manual review recommended

- **Knowledge Graph**: Performance limits with large graphs
  - Optimized for ~100 posts
  - Larger graphs may have slower rendering
  - Consider pagination for very large sites

### Performance Tips

- **Database Queries**: Use `select_related()` and `prefetch_related()`
  ```python
  BlogComment.objects.select_related('author').prefetch_related('replies')
  ```

- **Caching**: Cache expensive operations
  ```python
  from django.core.cache import cache
  result = cache.get_or_set('my_key', expensive_function, timeout=3600)
  ```

- **Image Optimization**: Optimize images before upload
  - Use WebP format when possible
  - Compress large images
  - Let the system generate multiple sizes automatically

- **Search Index**: Keep search index up to date
  ```bash
  python manage.py rebuild_search_index
  ```

### Support & Issues

For issues, questions, or contributions:
- **GitHub Issues**: [github.com/aaronspindler/aaronspindler.com/issues](https://github.com/aaronspindler/aaronspindler.com/issues)
- **Documentation**: This README
- **Code Examples**: See test files for usage patterns

### License

This project is licensed under the MIT License - see the LICENSE file for details.

### Acknowledgments

- Django community for the excellent framework
- Contributors and maintainers of all open-source dependencies
- Open source community for inspiration and tools

---

*Last Updated: October 2025*
