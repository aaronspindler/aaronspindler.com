# Test Data Factories

This directory contains reusable test data factories that provide consistent fake data across all test files in the project. The factories help eliminate code duplication and make tests more maintainable.

## Overview

The factory system provides:
- **Consistent test data** across all apps
- **Reduced code duplication** in test files
- **Easy-to-use factory methods** for creating test objects
- **Flexible configuration** with sensible defaults
- **Type-safe test data** generation

## Quick Reference

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

## Usage

### Basic Import

```python
from tests.factories import UserFactory, BlogCommentFactory, PageVisitFactory, PhotoFactory
```

### Using TestDataMixin

For test classes that need common setup, inherit from `TestDataMixin`:

```python
from tests.factories import TestDataMixin

class MyTestCase(TestCase, TestDataMixin):
    def setUp(self):
        self.setUp_users()  # Creates self.user, self.staff_user, self.superuser
        self.setUp_blog_data()  # Sets up self.comment_data, self.mock_blog_data
        self.setUp_photo_data()  # Sets up self.test_image, self.test_image_2
```

## Available Factories

### UserFactory

Creates test users with consistent data:

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

### BlogCommentFactory

Creates blog comments with proper defaults:

```python
# Basic comment with user
comment = BlogCommentFactory.create_comment(author=user)

# Anonymous comment
comment = BlogCommentFactory.create_anonymous_comment()

# Approved comment
comment = BlogCommentFactory.create_approved_comment()

# Pending comment (default status)
comment = BlogCommentFactory.create_pending_comment()

# Comment with custom data
comment = BlogCommentFactory.create_comment(
    content='Custom content',
    blog_template_name='custom_post',
    blog_category='personal',
    status='approved'
)

# Nested comment (reply)
reply = BlogCommentFactory.create_comment(
    parent=comment,
    content='This is a reply'
)

# Comment vote
vote = BlogCommentFactory.create_comment_vote(comment, user, 'upvote')
vote = BlogCommentFactory.create_comment_vote(comment, user, 'downvote', ip_address='192.168.1.1')
```

### PageVisitFactory

Creates page visit records:

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

### PhotoFactory

Creates photos and albums:

```python
# Basic photo with auto-generated test image
photo = PhotoFactory.create_photo()

# Photo with custom data
photo = PhotoFactory.create_photo(
    title='My Photo',
    description='Photo description',
    original_filename='vacation.jpg'
)

# Photo with EXIF data
photo = PhotoFactory.create_photo_with_exif(
    camera_make='Canon',
    camera_model='EOS R5',
    iso=400,
    aperture='f/2.8',
    shutter_speed='1/250',
    focal_length='50mm',
    date_taken=datetime(2024, 1, 1, 12, 0, 0)
)

# Photo album
album = PhotoFactory.create_photo_album(
    title='My Album',
    description='Album description',
    slug='my-album',
    is_private=False,
    allow_downloads=True
)

# Private album
private_album = PhotoFactory.create_photo_album(
    title='Private Photos',
    is_private=True
)

# Test image file (for custom use)
image = PhotoFactory.create_test_image(
    size=(200, 200),
    color=(0, 255, 0),  # RGB tuple
    format='JPEG'
)
```

### MockDataFactory

Provides common mock data:

```python
# Mock blog data for views
blog_data = MockDataFactory.get_mock_blog_data()

# Common IP addresses
ips = MockDataFactory.get_common_ip_addresses()

# Common form data
form_data = MockDataFactory.get_common_form_data()
```

## Best Practices

### 1. Use Factories Instead of Direct Model Creation

❌ **Don't do this:**
```python
user = User.objects.create_user(
    username='testuser',
    email='test@example.com',
    password='testpass123'
)
```

✅ **Do this:**
```python
user = UserFactory.create_user()
```

### 2. Use TestDataMixin for Common Setup

❌ **Don't repeat setup code:**
```python
def setUp(self):
    self.user = User.objects.create_user(...)
    self.staff_user = User.objects.create_user(..., is_staff=True)
    # ... repeated in many test classes
```

✅ **Use the mixin:**
```python
class MyTest(TestCase, TestDataMixin):
    def setUp(self):
        self.setUp_users()  # Sets up all common users
```

### 3. Customize Only What You Need

✅ **Override only specific fields:**
```python
# Good: Only override what's different
user = UserFactory.create_user(username='specific_user')

# Good: Use defaults for everything else
comment = BlogCommentFactory.create_comment(author=user)
```

### 4. Use Factory Methods for Common Patterns

✅ **Use specialized factory methods:**
```python
# Instead of setting status manually
approved_comment = BlogCommentFactory.create_approved_comment()

# Instead of setting up geo data manually
geo_visit = PageVisitFactory.create_visit_with_geo()
```

## Extending the Factories

To add new factory methods:

1. Add the method to the appropriate factory class
2. Follow the existing naming conventions
3. Provide sensible defaults
4. Add docstrings explaining the purpose
5. Update this README

Example:

```python
class UserFactory:
    @staticmethod
    def create_inactive_user(**kwargs):
        """Create an inactive user for testing account activation."""
        kwargs.setdefault('is_active', False)
        return UserFactory.create_user(**kwargs)
```

## Migration Guide

To migrate existing tests to use factories:

1. Import the appropriate factories
2. Replace direct model creation with factory calls
3. Update assertions to use factory-generated data
4. Consider using TestDataMixin for common setup
5. Run tests to ensure everything works

## Factory Design Principles

1. **Sensible Defaults**: Every factory should work without parameters
2. **Flexibility**: Allow customization of any field
3. **Consistency**: Use consistent naming and patterns
4. **Documentation**: Clear docstrings for all methods
5. **Type Safety**: Handle None vs empty string properly
6. **Relationships**: Handle related objects intelligently

## Special Cases and Notes

### Handling Duplicate Photo Detection
When creating photos with specific hashes for testing duplicate detection:
```python
# The Photo model has built-in duplicate checking
# Use mocks to bypass this when testing duplicate scenarios
with patch('photos.models.DuplicateDetector.find_duplicates'):
    photo = PhotoFactory.create_photo(file_hash='specific_hash')
```

### Creating Related Objects
```python
# Create photo and add to album
photo = PhotoFactory.create_photo()
album = PhotoFactory.create_photo_album()
album.photos.add(photo)

# Create comment with replies
parent = BlogCommentFactory.create_comment()
reply = BlogCommentFactory.create_comment(parent=parent)
```

### Testing with Geo Data
```python
# Create visit with specific location
visit = PageVisitFactory.create_visit_with_geo(
    country='Canada',
    city='Toronto',
    lat=43.6532,
    lon=-79.3832
)
```

## Recent Updates

### December 2024
- **Standardized all test files**: All tests in `accounts/`, `blog/`, `pages/`, and `photos/` apps now use factories
- **Added `create_pending_comment()`**: New method for creating pending comments
- **Enhanced PhotoFactory**: Added support for EXIF data and album creation
- **Improved UserFactory**: Added consistent user creation with automatic unique usernames
- **Updated documentation**: Comprehensive README with all factory methods and patterns

## Test Apps Using Factories

The following test modules have been updated to use these factories:

### Accounts App
- `accounts/tests/test_models.py` - Uses UserFactory
- `accounts/tests/test_views.py` - Uses UserFactory
- `accounts/tests/test_admin.py` - Uses UserFactory
- `accounts/tests/test_forms.py` - Uses UserFactory

### Blog App
- `blog/tests/test_models.py` - Uses BlogCommentFactory, UserFactory
- `blog/tests/test_views.py` - Uses BlogCommentFactory, UserFactory, MockDataFactory
- `blog/tests/test_admin.py` - Uses BlogCommentFactory, UserFactory
- `blog/tests/test_forms.py` - Uses BlogCommentFactory, UserFactory

### Pages App
- `pages/tests/test_models.py` - Uses PageVisitFactory
- `pages/tests/test_views.py` - Uses PhotoFactory, UserFactory
- `pages/tests/test_admin.py` - Uses PageVisitFactory, UserFactory

### Photos App
- `photos/tests/test_views.py` - Uses PhotoFactory, UserFactory
- `photos/tests/test_forms.py` - Uses PhotoFactory
- `photos/tests/test_signals.py` - Uses PhotoFactory
