# Testing Guide

## Overview

Comprehensive testing setup using Django's built-in test framework, factory-based test data generation, and Docker-based test environments for consistent, reproducible testing.

## Quick Start

```bash
# Run all tests locally
python manage.py test

# Run with coverage reporting
coverage run --source='.' manage.py test --no-input
coverage report
coverage html  # View detailed report in htmlcov/index.html

# Run tests in Docker (recommended)
make test

# Run specific app tests
make test-run-app APP=blog

# Security audit
safety check
```

## Test Data Factories

### Overview

The project uses a comprehensive factory system with app-specific factories for consistent test data. Each app has its own `tests/factories.py` module:

- `accounts.tests.factories` - UserFactory
- `blog.tests.factories` - BlogCommentFactory, MockDataFactory
- `photos.tests.factories` - PhotoFactory

For backward compatibility, all factories are also available from `tests.factories` (deprecated).

### Available Factories

#### UserFactory

Create test users with various permission levels:

```python
from accounts.tests.factories import UserFactory

# Create regular user
user = UserFactory.create_user()

# Create with custom attributes
user = UserFactory.create_user(
    username='johndoe',
    email='john@example.com',
    first_name='John',
    last_name='Doe'
)

# Create staff user
staff = UserFactory.create_staff_user()

# Create superuser
admin = UserFactory.create_superuser()
```

#### BlogCommentFactory

Create blog comments and votes:

```python
from blog.tests.factories import BlogCommentFactory

# Create comment
comment = BlogCommentFactory.create_comment(author=user)

# Create anonymous comment
anonymous = BlogCommentFactory.create_anonymous_comment()

# Create approved comment
approved = BlogCommentFactory.create_approved_comment()

# Create reply to comment
reply = BlogCommentFactory.create_comment(parent=comment)

# Create comment vote
vote = BlogCommentFactory.create_comment_vote(
    comment=comment,
    user=user,
    vote_type='upvote'
)
```

#### PhotoFactory

Create photos with auto-generated test images:

```python
from photos.tests.factories import PhotoFactory

# Create photo with auto-generated image
photo = PhotoFactory.create_photo()

# Create photo with EXIF metadata
photo = PhotoFactory.create_photo_with_exif(
    camera_make='Canon',
    camera_model='EOS R5',
    iso=400,
    aperture=2.8,
    location='San Francisco, CA'
)

# Create photo album
album = PhotoFactory.create_photo_album(
    title='My Album',
    is_private=False
)

# Add photos to album
photos = [PhotoFactory.create_photo() for _ in range(5)]
album.photos.add(*photos)
```

### TestDataMixin

Use the mixin for easy access to all factories:

```python
from django.test import TestCase
from tests.factories import TestDataMixin

class MyTestCase(TestDataMixin, TestCase):
    def test_example(self):
        # Create test user
        user = self.create_user()

        # Create blog comment
        comment = self.create_comment(author=user)

        # Create page visit
        visit = self.create_visit()

        # Create photo
        photo = self.create_photo()
```

## Test Structure

### Directory Organization

```
app_name/
├── tests/
│   ├── __init__.py
│   ├── test_models.py      # Model tests
│   ├── test_views.py       # View tests
│   ├── test_forms.py       # Form tests
│   ├── test_utils.py       # Utility function tests
│   └── test_integration.py # Integration tests
```

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `*Test` or `Test*`
- Test methods: `test_*`

```python
class BlogCommentModelTest(TestCase):
    """Test BlogComment model."""

    def test_create_comment(self):
        """Test creating a blog comment."""
        pass

    def test_comment_str(self):
        """Test comment string representation."""
        pass
```

## Docker Test Environment

### Architecture

```
┌────────────────────────────────────────────────────────┐
│           Docker Test Network (Optimized)              │
├──────────────┬──────────────┬──────────────────────────┤
│  PostgreSQL  │    Redis     │      Test Runner         │
│  (Database)  │  (Cache/MQ)  │  (Django + Playwright)   │
│    :5433     │    :6380     │        :8001             │
└──────────────┴──────────────┴──────────────────────────┘
```

### Optimizations

- **FileSystemStorage**: No S3 mocking = 60-90% faster
- **No External Services**: Simple 2-service setup (postgres + redis)
- **Faster Startup**: ~10s vs ~40s with LocalStack
- **Minimal Dependencies**: Only essential services

### Docker Commands

```bash
# Run complete test suite
make test

# Run tests for specific app
make test-run-app APP=blog
make test-run-app APP=photos

# Run specific test class or method
make test-run-specific TEST=blog.tests.test_models.BlogCommentModelTest
make test-run-specific TEST=blog.tests.test_models.BlogCommentModelTest.test_create_comment

# Run with coverage
make test-coverage

# Manage test environment
make test-up      # Start test services
make test-down    # Stop test services
make test-logs    # View logs
make test-shell   # Open Django shell in test container
make test-clean   # Stop and remove volumes
```

### docker-compose.test.yml

Configuration highlights:

```yaml
services:
  postgres_test:
    image: postgres:15
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_pass
    ports:
      - "5433:5432"

  redis_test:
    image: redis:7
    ports:
      - "6380:6379"

  test:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://test_user:test_pass@postgres_test:5432/test_db
      REDIS_URL: redis://redis_test:6379/0
      DJANGO_SETTINGS_MODULE: config.settings_test
    depends_on:
      - postgres_test
      - redis_test
    command: python manage.py test --no-input
```

### Test Settings

**File**: `config/settings_test.py`

```python
from .settings import *

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# In-memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# FileSystemStorage instead of S3 (faster)
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Disable migrations for faster tests (optional)
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()
```

## Writing Tests

### Model Tests

```python
from django.test import TestCase
from accounts.tests.factories import UserFactory
from blog.tests.factories import BlogCommentFactory

class BlogCommentModelTest(TestCase):
    """Test BlogComment model."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory.create_user()
        self.comment = BlogCommentFactory.create_comment(author=self.user)

    def test_create_comment(self):
        """Test creating a blog comment."""
        self.assertIsNotNone(self.comment.id)
        self.assertEqual(self.comment.author, self.user)

    def test_comment_str(self):
        """Test comment string representation."""
        expected = f"Comment by {self.user.username}"
        self.assertEqual(str(self.comment), expected)

    def test_approved_comments(self):
        """Test filtering approved comments."""
        approved = BlogCommentFactory.create_approved_comment()
        comments = BlogComment.objects.filter(is_approved=True)
        self.assertIn(approved, comments)
        self.assertNotIn(self.comment, comments)
```

### View Tests

```python
from django.test import TestCase, Client
from django.urls import reverse
from accounts.tests.factories import UserFactory

class HomeViewTest(TestCase):
    """Test home page view."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_home_page_status_code(self):
        """Test home page returns 200."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_home_page_template(self):
        """Test home page uses correct template."""
        response = self.client.get(reverse('home'))
        self.assertTemplateUsed(response, 'pages/home.html')

    def test_home_page_context(self):
        """Test home page context contains expected data."""
        response = self.client.get(reverse('home'))
        self.assertIn('blog_posts', response.context)

class AuthenticatedViewTest(TestCase):
    """Test views requiring authentication."""

    def setUp(self):
        """Set up authenticated client."""
        self.user = UserFactory.create_user()
        self.client = Client()
        self.client.force_login(self.user)

    def test_authenticated_access(self):
        """Test authenticated user can access view."""
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
```

### Form Tests

```python
from django.test import TestCase
from blog.forms import CommentForm
from accounts.tests.factories import UserFactory

class CommentFormTest(TestCase):
    """Test comment form."""

    def test_valid_form(self):
        """Test form with valid data."""
        data = {
            'content': 'Great post!',
            'author_name': 'John Doe',
            'author_email': 'john@example.com',
        }
        form = CommentForm(data=data)
        self.assertTrue(form.is_valid())

    def test_invalid_email(self):
        """Test form with invalid email."""
        data = {
            'content': 'Great post!',
            'author_name': 'John Doe',
            'author_email': 'invalid-email',
        }
        form = CommentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('author_email', form.errors)

    def test_required_fields(self):
        """Test form requires content."""
        form = CommentForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)
```

### API Tests

```python
from django.test import TestCase
from django.urls import reverse
import json

class APITest(TestCase):
    """Test API endpoints."""

    def test_knowledge_graph_api(self):
        """Test knowledge graph API returns valid JSON."""
        response = self.client.get(reverse('api_knowledge_graph'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

        data = json.loads(response.content)
        self.assertIn('nodes', data['data'])
        self.assertIn('edges', data['data'])

    def test_search_autocomplete_api(self):
        """Test search autocomplete API."""
        response = self.client.get(
            reverse('api_search_autocomplete'),
            {'q': 'django'}
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertIn('suggestions', data)
```

### Integration Tests

```python
from django.test import TestCase
from accounts.tests.factories import UserFactory
from photos.tests.factories import PhotoFactory

class PhotoUploadIntegrationTest(TestCase):
    """Test complete photo upload workflow."""

    def test_photo_upload_workflow(self):
        """Test uploading photo generates all sizes."""
        # Create photo
        photo = PhotoFactory.create_photo(
            title='Test Photo',
            location='San Francisco, CA'
        )

        # Check all sizes generated
        self.assertTrue(photo.original_image)
        self.assertTrue(photo.large_image)
        self.assertTrue(photo.medium_image)
        self.assertTrue(photo.small_image)
        self.assertTrue(photo.thumbnail_image)

        # Check EXIF extracted
        self.assertIsNotNone(photo.camera_make)

        # Check search index updated
        self.assertIsNotNone(photo.search_vector)
```

## Coverage Reporting

### Running with Coverage

```bash
# Run tests with coverage
coverage run --source='.' manage.py test --no-input

# View coverage report
coverage report

# Generate HTML report
coverage html

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Configuration

**File**: `.coveragerc`

```ini
[run]
source = .
omit =
    */migrations/*
    */tests/*
    */test_*.py
    */__pycache__/*
    */venv/*
    */staticfiles/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

### Coverage Targets

- **Overall**: > 80%
- **Critical code**: > 90%
- **New features**: 100%

## CI/CD Testing

### GitHub Actions

**File**: `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        env:
          DATABASE_URL: postgresql://test_user:test_pass@localhost/test_db
          REDIS_URL: redis://localhost:6379/0
        run: |
          coverage run --source='.' manage.py test --parallel
          coverage report
          coverage xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Performance Testing

### Load Testing with Locust

```python
# locustfile.py
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def view_home(self):
        self.client.get("/")

    @task(2)
    def view_blog_post(self):
        self.client.get("/b/tech/django-tutorial/")

    @task(1)
    def search(self):
        self.client.get("/api/search/autocomplete/?q=django")
```

Run load tests:
```bash
locust -f locustfile.py --host=http://localhost:8000
```

## Best Practices

### Test Organization

1. **One test case per model/view/form**
2. **Group related tests in classes**
3. **Use descriptive test names**
4. **Keep tests independent**
5. **Use factories for test data**

### Test Data

1. **Use factories instead of fixtures**
2. **Create minimal data needed**
3. **Clean up in tearDown if needed**
4. **Don't rely on order of execution**

### Assertions

1. **Use specific assertions** (`assertEqual`, `assertIn`, etc.)
2. **Test one thing per test method**
3. **Include helpful failure messages**
4. **Test both success and failure cases**

### Performance

1. **Use `setUpTestData` for read-only data**
2. **Disable migrations if appropriate**
3. **Use in-memory cache**
4. **Mock external services**

## Troubleshooting

### Tests Failing Locally But Pass in CI

**Solutions**:
1. Check environment variables
2. Verify database state (old test data?)
3. Check Python/Django versions match
4. Clear `__pycache__` directories
5. Check for timezone issues

### Slow Tests

**Solutions**:
1. Use `setUpTestData` instead of `setUp`
2. Disable migrations: `--no-migrations`
3. Use faster password hasher in test settings
4. Mock slow operations (API calls, file I/O)
5. Run with `--parallel` (CI only)

### Database Errors

**Solutions**:
1. Ensure test database exists
2. Check PostgreSQL extensions installed
3. Verify database permissions
4. Clear old test databases: `python manage.py test --keepdb`
5. Check for transaction issues

### Import Errors

**Solutions**:
1. Verify virtual environment activated
2. Check `PYTHONPATH` includes project root
3. Install test dependencies: `pip install -r requirements-dev.txt`
4. Check for circular imports

## Related Documentation

- [Architecture](architecture.md) - Project structure
- [Management Commands](commands.md) - Test-related commands
- [Deployment](deployment.md) - Production testing
- Test Data Factories: `tests/factories.py`
