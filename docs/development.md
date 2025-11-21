# Development Guide

*Last Updated: November 2024*

This guide covers the complete development process for aaronspindler.com, including environment setup, build processes, code style, Git workflow, and best practices.

## Table of Contents

- [Environment Setup](#environment-setup)
- [Development Workflow](#development-workflow)
- [Build Processes](#build-processes)
- [Code Style & Quality](#code-style--quality)
- [Git Workflow](#git-workflow)
- [Testing](#testing)
- [Docker Development](#docker-development)
- [Debugging](#debugging)

## Environment Setup

### Prerequisites

- **Python 3.13**: Required Python version
- **Node.js 18+**: For frontend tooling
- **PostgreSQL 16**: Main database
- **Redis 7**: Caching and Celery broker
- **QuestDB 8.2.1**: Time-series data (for FeeFiFoFunds)
- **Docker & Docker Compose**: Container development

### Initial Setup

#### 1. Clone Repository

```bash
git clone https://github.com/aaronspindler/aaronspindler.com.git
cd aaronspindler.com
```

#### 2. Python Environment

```bash
# Create virtual environment
python3.13 -m venv venv

# Activate environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install uv for faster package installation
pip install uv

# Install dependencies
uv pip install -r requirements/base.txt -r requirements/local.txt
```

#### 3. Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
vim .env
```

**Required environment variables**:
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/aaronspindler_dev

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# AWS S3 (for media files)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=your-bucket

# QuestDB (for FeeFiFoFunds)
QUESTDB_HOST=localhost
QUESTDB_PORT=8812

# Development settings
DEBUG=True
SECRET_KEY=your-development-secret-key
```

#### 4. Database Setup

```bash
# Create database
createdb aaronspindler_dev

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load sample data (if available)
python manage.py loaddata fixtures/sample_data.json
```

#### 5. Frontend Setup

```bash
# Install Node dependencies
npm install

# Build CSS
npm run build:css

# Build JavaScript
npm run build:js
```

#### 6. Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files (initial check)
pre-commit run --all-files
```

## Development Workflow

### Running the Development Server

```bash
# Standard Django server
python manage.py runserver

# With Werkzeug debugger (better errors)
python manage.py runserver_plus

# Access at http://localhost:8000
```

### Running Services

#### Start All Services (Docker)

```bash
# Start PostgreSQL, Redis, QuestDB
docker-compose -f docker-compose.dev.yml up -d

# Check service health
docker-compose -f docker-compose.dev.yml ps
```

#### Start Services Individually

```bash
# PostgreSQL
pg_ctl -D /usr/local/var/postgres start

# Redis
redis-server

# QuestDB
questdb start

# Celery Worker
celery -A config.celery_app worker --loglevel=info

# Celery Beat
celery -A config.celery_app beat --loglevel=info

# Flower (monitoring)
celery -A config.celery_app flower
```

### Development Commands

```bash
# Create new Django app
python manage.py startapp myapp

# Make migrations
python manage.py makemigrations

# Show migration SQL
python manage.py sqlmigrate app_name 0001

# Django shell with enhanced features
python manage.py shell_plus

# Database shell
python manage.py dbshell

# Show URLs
python manage.py show_urls
```

## Build Processes

### CSS Pipeline

The project uses PostCSS for CSS processing:

```bash
# Build CSS with optimizations
python manage.py build_css

# Watch for CSS changes (development)
npm run watch:css

# Build for production
npm run build:css:prod
```

**PostCSS Pipeline**:
1. **Autoprefixer**: Adds vendor prefixes
2. **PurgeCSS**: Removes unused styles
3. **CSSnano**: Minification and optimization
4. **Critical CSS**: Extracts critical path CSS

**Configuration** (`.config/postcss.config.js`):
```javascript
module.exports = {
  plugins: [
    require('autoprefixer'),
    require('cssnano')({
      preset: 'default',
    }),
    ...(process.env.NODE_ENV === 'production' ? [
      require('@fullhuman/postcss-purgecss')({
        content: ['templates/**/*.html', 'apps/**/*.py'],
        defaultExtractor: content => content.match(/[\w-/:]+(?<!:)/g) || []
      })
    ] : [])
  ]
}
```

### JavaScript Pipeline

JavaScript optimization with Terser:

```bash
# Build JavaScript
npm run build:js

# Minify for production
npm run build:js:prod

# Watch for changes
npm run watch:js
```

**Build Scripts**:
```json
{
  "scripts": {
    "build:js": "terser static/js/base.js -o static/js/base-optimized.js",
    "build:js:prod": "terser static/js/*.js -c -m -o static/js/bundle.min.js",
    "watch:js": "nodemon --watch static/js --exec npm run build:js"
  }
}
```

### Static Files

```bash
# Collect static files
python manage.py collectstatic

# Collect with optimization
python manage.py collectstatic_optimize

# Clear static files
python manage.py collectstatic --clear --noinput
```

### Image Optimization

```bash
# Generate responsive images
python manage.py process_photos --all

# Generate album ZIP files
python manage.py generate_album_zips --all

# Optimize existing images
python manage.py optimize_images
```

## Code Style & Quality

### Python Code Style

**Configuration** (`pyproject.toml`):
```toml
[tool.ruff]
line-length = 120
target-version = "py313"
select = [
    "E",   # pycodestyle errors
    "F",   # Pyflakes
    "W",   # pycodestyle warnings
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "DJ",  # flake8-django
    "RUF", # Ruff-specific
]

[tool.ruff.per-file-ignores]
"*/migrations/*" = ["E501"]
"*/tests/*" = ["F403", "F405"]
```

**Running Linters**:
```bash
# Ruff (linting and formatting)
ruff check .
ruff format .

# Type checking
mypy .

# Security scanning
bandit -r apps/

# Django checks
python manage.py check --deploy
```

### JavaScript/CSS Code Style

**Prettier Configuration** (`.config/.prettierrc`):
```json
{
  "printWidth": 120,
  "tabWidth": 2,
  "useTabs": false,
  "semi": true,
  "singleQuote": true,
  "trailingComma": "es5"
}
```

**Running Formatters**:
```bash
# Format CSS
npx prettier --write "static/css/**/*.css"

# Format JavaScript
npx prettier --write "static/js/**/*.js"
```

### Pre-commit Hooks

**Configuration** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.0.3
    hooks:
      - id: prettier
        files: \.(css|scss|sass)$

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets

  - repo: local
    hooks:
      - id: check-minified-css
        name: Check for minified CSS
        entry: scripts/check_minified_css.py
        language: python
        files: \.css$
```

## Git Workflow

### Branch Strategy

```bash
# Main branches
main          # Production-ready code
develop       # Integration branch (optional)

# Feature branches
feature/add-user-profile
feature/optimize-search

# Bugfix branches
bugfix/fix-login-error
bugfix/correct-timezone

# Hotfix branches (production fixes)
hotfix/security-patch
```

### Commit Convention

**Format**: `type(scope): description`

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test changes
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

**Examples**:
```bash
git commit -m "feat(photos): add EXIF data extraction"
git commit -m "fix(auth): correct password reset flow"
git commit -m "docs(api): update endpoint documentation"
git commit -m "perf(search): optimize full-text queries"
```

### Pull Request Process

1. **Create feature branch**:
```bash
git checkout -b feature/my-feature
```

2. **Make changes and commit**:
```bash
git add .
git commit -m "feat: add new feature"
```

3. **Push to GitHub**:
```bash
git push origin feature/my-feature
```

4. **Create Pull Request**:
```bash
# Using GitHub CLI
gh pr create --title "Add new feature" --body "Description..."
```

5. **Review checklist**:
- [ ] Tests pass
- [ ] Pre-commit hooks pass
- [ ] Documentation updated
- [ ] No security issues
- [ ] Code reviewed

## Testing

### Running Tests

```bash
# Run all tests
python manage.py test

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html

# Run specific app tests
python manage.py test apps.blog

# Run specific test
python manage.py test apps.blog.tests.test_models.BlogPostTest

# Run with parallel execution
python manage.py test --parallel

# Run with verbose output
python manage.py test --verbosity=2
```

### Test Database

```bash
# Use separate test database
TEST_DATABASE_URL=postgresql://user:pass@localhost/test_db

# Keep test database after tests
python manage.py test --keepdb

# Debug test database
python manage.py test --debug-sql
```

### Writing Tests

**Example Test**:
```python
from django.test import TestCase
from django.urls import reverse
from apps.blog.models import BlogPost

class BlogPostTestCase(TestCase):
    def setUp(self):
        self.post = BlogPost.objects.create(
            title="Test Post",
            slug="test-post",
            content="Test content"
        )

    def test_post_creation(self):
        actual = self.post.title
        expected = "Test Post"
        message = f"Found {actual}, expected {expected}"
        self.assertEqual(actual, expected, message)

    def test_post_url(self):
        response = self.client.get(reverse('blog:post', args=[self.post.slug]))
        self.assertEqual(response.status_code, 200)
```

## Docker Development

### Local Docker Development

```bash
# Build development image
docker build -f deployment/Dockerfile --target development -t aaronspindler-dev .

# Run with volume mounts
docker run -it \
  -v $(pwd):/app \
  -p 8000:8000 \
  --env-file .env \
  aaronspindler-dev

# Use Docker Compose
docker-compose -f docker-compose.dev.yml up
```

### Docker Compose Development

**docker-compose.dev.yml**:
```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: deployment/Dockerfile
      target: development
    volumes:
      - .:/app
      - /app/node_modules
    ports:
      - "8000:8000"
    environment:
      - DEBUG=True
    command: python manage.py runserver 0.0.0.0:8000

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=aaronspindler_dev
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  questdb:
    image: questdb/questdb:8.2.1
    ports:
      - "9000:9000"
      - "8812:8812"
```

### Debugging Docker

```bash
# View logs
docker-compose logs -f web

# Execute commands in container
docker-compose exec web python manage.py shell

# Access container shell
docker-compose exec web /bin/bash

# Inspect container
docker inspect <container-id>

# Check resource usage
docker stats
```

## Debugging

### Django Debug Toolbar

```python
# settings/local.py
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1', 'localhost']

# urls.py
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
```

### Python Debugging

```python
# Using pdb
import pdb; pdb.set_trace()

# Using ipdb (enhanced)
import ipdb; ipdb.set_trace()

# Using breakpoint() (Python 3.7+)
breakpoint()

# Django shell_plus
python manage.py shell_plus --print-sql
```

### Database Debugging

```bash
# Show SQL queries
python manage.py shell_plus --print-sql

# Log all SQL queries
# settings/local.py
LOGGING = {
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    }
}
```

### Performance Profiling

```bash
# Django Silk (request profiling)
pip install django-silk

# Line profiler
pip install line_profiler
kernprof -l -v script.py

# Memory profiler
pip install memory_profiler
python -m memory_profiler script.py
```

## Development Tips

### Makefile Commands

The project includes a Makefile for common tasks:

```bash
# Run tests
make test

# Format code
make format

# Lint code
make lint

# Build static files
make static

# Clean compiled files
make clean

# Full development setup
make setup
```

### Useful Django Extensions

```bash
# Django Extensions commands
python manage.py show_urls              # Display all URLs
python manage.py graph_models -a        # Generate model graphs
python manage.py validate_templates     # Check template syntax
python manage.py unreferenced_files     # Find unused media files
python manage.py print_settings         # Show current settings
```

### Environment-Specific Settings

```python
# config/settings/__init__.py
import os

env = os.environ.get('DJANGO_ENV', 'local')

if env == 'production':
    from .production import *
elif env == 'test':
    from .test import *
else:
    from .local import *
```

### Database Optimization

```bash
# Analyze slow queries
python manage.py debugsqlshell

# Database vacuum (PostgreSQL)
python manage.py dbshell
VACUUM ANALYZE;

# Reset sequences
python manage.py sqlsequencereset app_name
```

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Reinstall dependencies
pip install --force-reinstall -r requirements/base.txt
```

#### Migration Issues
```bash
# Reset migrations
python manage.py migrate app_name zero
python manage.py makemigrations app_name
python manage.py migrate app_name

# Fake migrations
python manage.py migrate --fake app_name
```

#### Static Files Issues
```bash
# Clear and rebuild
python manage.py collectstatic --clear --noinput
python manage.py build_css
npm run build:js
```

#### Docker Issues
```bash
# Clean Docker system
docker system prune -a
docker volume prune

# Rebuild without cache
docker-compose build --no-cache
```

## Related Documentation

- [Architecture Overview](infrastructure/architecture.md) - System design
- [Testing Guide](testing.md) - Comprehensive testing documentation
- [CI/CD Pipeline](features/ci-cd.md) - Automated testing and deployment
- [Commands Reference](commands.md) - All management commands
- [Deployment Guide](deployment.md) - Production deployment
- [Quick Start Guide](quick-start.md) - Fast setup for new developers
