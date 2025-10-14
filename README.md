# aaronspindler.com

> *A Django-powered personal website with a twist - featuring interactive knowledge graphs, smart photo management, and a blog system that thinks outside the database*

📚 **[View Complete Documentation](./DOCUMENTATION.md)** - Comprehensive guide with all features, setup instructions, and API reference

## Quick Links

- 📖 [Complete Documentation](./DOCUMENTATION.md) - All-in-one documentation
- 🚀 [Getting Started](./DOCUMENTATION.md#getting-started) - Setup and installation
- 🧪 [Testing Guide](./DOCUMENTATION.md#testing) - Test factories and Docker testing
- 🔧 [Development Guide](./DOCUMENTATION.md#development-guide) - Commands and architecture
- 📦 [Deployment](./DOCUMENTATION.md#deployment) - Production configuration
- 📡 [API Reference](./DOCUMENTATION.md#api-reference) - Endpoint documentation
- ⚙️ [Management Commands](#management-commands) - Custom Django management commands

[![Django](https://img.shields.io/badge/Django-5.2.5-green?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)

## ( What Makes This Site Special

This isn't your average personal website. It's a playground for web experiments and a showcase of what happens when you give Django some creative freedom.

### < Key Features

- **= Interactive Knowledge Graph** - Watch your blog posts connect in real-time with a D3.js-powered visualization that maps relationships between posts (now with enhanced stability for large graphs)
- **= Smart Photo Management** - Upload once, get 5 optimized sizes automatically, complete with EXIF data extraction
- **= Template-Based Blog System** - No database clutter - blog posts live as HTML templates with rich metadata
- **= Automated Performance Monitoring** - Nightly Lighthouse audits tracking 4 key metrics with historical trends and badge display
- **= Privacy-First Analytics** - Custom page visit tracking that respects user privacy
- **< Server-Side Screenshots** - Playwright-powered screenshot generation for social media previews
- ** Performance Optimized** - Static file compression, multi-stage Docker builds, and intelligent caching

## = Tech Stack

- **Framework**: Django 5.2.5 with Python 3.13
- **Database**: PostgreSQL with psycopg3
- **Storage**: AWS S3 (optional) via django-storages
- **Authentication**: django-allauth for flexible auth options
- **Image Processing**: Pillow with automatic WebP generation
- **Screenshot Generation**: Playwright for server-side rendering
- **Server**: Gunicorn with WhiteNoise for static files
- **Containerization**: Docker with health checks

## = Quick Start

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

# Fire it up!
python manage.py runserver
```

Visit `http://localhost:8000` and enjoy! <

## =3 Docker Deployment

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

## = Creating Blog Posts

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

## < Knowledge Graph Magic

The knowledge graph automatically visualizes relationships between your blog posts with enhanced stability for large networks:

```bash
# Generate a high-quality screenshot of your knowledge graph
python manage.py generate_knowledge_graph_screenshot \
  --width 2400 \
  --height 1600 \
  --quality 100 \
  --transparent
```

## = Photo Management

Upload photos through the admin panel and get:
- = **5 optimized sizes** (thumbnail, small, medium, large, original)
- = **EXIF data extraction** (camera, lens, GPS coordinates)
- = **Automatic WebP conversion** for modern browsers
- = **S3 storage support** for production

## > Testing

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

## = Performance Features

- **Lighthouse Monitoring**: Automated nightly audits tracking Performance, Accessibility, Best Practices, and SEO scores with 30-day history visualization
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

### Common Workflows

**Complete build pipeline for production:**
```bash
python manage.py build_css  # Build and optimize CSS
python manage.py optimize_js  # Optimize JavaScript
python manage.py collectstatic_optimize  # Collect and optimize static files
python manage.py rebuild_knowledge_graph  # Rebuild knowledge graph
python manage.py generate_knowledge_graph_screenshot --width 2400 --height 1600 --quality 100
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
pre-commit run ruff --all-files
pre-commit run black --all-files

# Update hooks to latest versions
pre-commit autoupdate

# Skip hooks if needed (not recommended)
git commit --no-verify
git push --no-verify
```

The pre-commit hooks match CI/CD exactly:
- **On commit:** Ruff (auto-fix), Black (format), isort (sort imports), file checks
- **On push:** MyPy (type checking), Django system checks
- All auto-fix formatting issues where possible
