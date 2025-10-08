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

[![Django](https://img.shields.io/badge/Django-5.2.5-green?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)

## ( What Makes This Site Special

This isn't your average personal website. It's a playground for web experiments and a showcase of what happens when you give Django some creative freedom.

### < Key Features

- **= Interactive Knowledge Graph** - Watch your blog posts connect in real-time with a D3.js-powered visualization that maps relationships between posts
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

# Install Playwright browsers
playwright install chromium

# Set up environment variables
cp .env.example .env  # Edit with your settings

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

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

Blog posts are HTML templates - no admin panel needed! Create a new post:

1. Add your template to `templates/blog/<category>/<post-name>.html`
2. Include metadata blocks:

```django
{% block meta_title %}Your Awesome Post Title{% endblock %}
{% block meta_description %}A compelling description{% endblock %}
{% block meta_publish_date %}2024-01-01{% endblock %}
{% block meta_post_type %}tech{% endblock %}
{% block meta_reading_time %}5{% endblock %}

{% block content %}
  <h1>Your post content here!</h1>
{% endblock %}
```

3. Rebuild the knowledge graph:
```bash
python manage.py rebuild_knowledge_graph
```

## < Knowledge Graph Magic

The knowledge graph automatically visualizes relationships between your blog posts:

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