"""
Test data factories for creating consistent fake data across all tests.

This module provides factory functions to create test instances with
consistent, realistic fake data that can be reused across all test files.
"""

import uuid
from datetime import datetime
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

User = get_user_model()


class UserFactory:
    """Factory for creating test users with consistent data."""

    @staticmethod
    def create_user(username=None, email=None, password="testpass123", **kwargs):
        """Create a regular user with optional custom fields."""
        if not username:
            username = f"testuser_{uuid.uuid4().hex[:8]}"
        if email is None:
            email = f"{username}@example.com"

        return User.objects.create_user(username=username, email=email, password=password, **kwargs)

    @staticmethod
    def create_staff_user(username=None, email=None, password="testpass123", **kwargs):
        """Create a staff user with optional custom fields."""
        if not username:
            username = f"staff_{uuid.uuid4().hex[:8]}"
        if email is None:
            email = f"{username}@example.com"

        return User.objects.create_user(username=username, email=email, password=password, is_staff=True, **kwargs)

    @staticmethod
    def create_superuser(username=None, email=None, password="testpass123", **kwargs):
        """Create a superuser with optional custom fields."""
        if not username:
            username = f"admin_{uuid.uuid4().hex[:8]}"
        if email is None:
            email = f"{username}@example.com"

        return User.objects.create_superuser(username=username, email=email, password=password, **kwargs)

    @staticmethod
    def get_common_user_data():
        """Get common user data for form testing."""
        unique_id = uuid.uuid4().hex[:8]
        return {
            "username": f"testuser_{unique_id}",
            "email": f"test_{unique_id}@example.com",
            "password": "testpass123",
        }


class BlogCommentFactory:
    """Factory for creating test blog comments."""

    @staticmethod
    def create_comment(
        blog_template_name="0001_test_post",
        blog_category="tech",
        content="This is a test comment",
        author=None,
        author_name=None,
        author_email=None,
        status="pending",
        parent=None,
        **kwargs,
    ):
        """Create a blog comment with default test data."""
        from blog.models import BlogComment

        # If author is provided but no author_name, set author_name to empty string
        if author and author_name is None:
            author_name = ""
        # If no author but no author_name provided, use default
        elif not author and author_name is None:
            author_name = "Anonymous"

        # Similar logic for author_email
        if author and author_email is None:
            author_email = ""
        elif not author and author_email is None:
            author_email = "anonymous@example.com"

        return BlogComment.objects.create(
            blog_template_name=blog_template_name,
            blog_category=blog_category,
            content=content,
            author=author,
            author_name=author_name,
            author_email=author_email,
            status=status,
            parent=parent,
            **kwargs,
        )

    @staticmethod
    def create_approved_comment(**kwargs):
        """Create an approved comment."""
        kwargs.setdefault("status", "approved")
        return BlogCommentFactory.create_comment(**kwargs)

    @staticmethod
    def create_pending_comment(**kwargs):
        """Create a pending comment."""
        kwargs.setdefault("status", "pending")
        return BlogCommentFactory.create_comment(**kwargs)

    @staticmethod
    def create_anonymous_comment(author_name="John Doe", author_email="john@example.com", **kwargs):
        """Create an anonymous comment."""
        return BlogCommentFactory.create_comment(
            author=None, author_name=author_name, author_email=author_email, **kwargs
        )

    @staticmethod
    def create_comment_vote(comment, user, vote_type="upvote", ip_address=None, **kwargs):
        """Create a comment vote."""
        from blog.models import CommentVote

        return CommentVote.objects.create(
            comment=comment,
            user=user,
            vote_type=vote_type,
            ip_address=ip_address,
            **kwargs,
        )


# PageVisitFactory removed - request tracking now handled by RequestFingerprint in utils app


class PhotoFactory:
    """Factory for creating test photos."""

    @staticmethod
    def create_test_image(size=(100, 100), color=(255, 0, 0), format="JPEG"):
        """Create a test image file."""
        img = Image.new("RGB", size, color)
        img_io = BytesIO()
        img.save(img_io, format=format)
        img_io.seek(0)
        return SimpleUploadedFile(name="test.jpg", content=img_io.getvalue(), content_type="image/jpeg")

    @staticmethod
    def create_photo(
        title="Test Photo",
        description="Test Description",
        image=None,
        original_filename=None,
        **kwargs,
    ):
        """Create a photo with default test data."""
        from photos.models import Photo

        if image is None:
            image = PhotoFactory.create_test_image()

        photo = Photo(
            title=title,
            description=description,
            image=image,
            original_filename=original_filename,
            **kwargs,
        )
        photo.save(skip_duplicate_check=True)
        return photo

    @staticmethod
    def create_photo_with_exif(
        camera_make="Canon",
        camera_model="EOS R5",
        iso=400,
        aperture="f/2.8",
        shutter_speed="1/250",
        focal_length="50mm",
        date_taken=None,
        **kwargs,
    ):
        """Create a photo with EXIF data."""
        if date_taken is None:
            date_taken = datetime(2024, 1, 1, 12, 0, 0)

        return PhotoFactory.create_photo(
            camera_make=camera_make,
            camera_model=camera_model,
            iso=iso,
            aperture=aperture,
            shutter_speed=shutter_speed,
            focal_length=focal_length,
            date_taken=date_taken,
            **kwargs,
        )

    @staticmethod
    def create_photo_album(
        title="Test Album",
        description="Test Description",
        is_private=False,
        allow_downloads=False,
        slug=None,
        **kwargs,
    ):
        """Create a photo album with default test data."""
        from photos.models import PhotoAlbum

        return PhotoAlbum.objects.create(
            title=title,
            description=description,
            is_private=is_private,
            allow_downloads=allow_downloads,
            slug=slug,
            **kwargs,
        )


class MockDataFactory:
    """Factory for creating mock blog data."""

    @staticmethod
    def get_mock_blog_data(
        entry_number="0001",
        template_name="0001_test_post",
        blog_title="0001 test post",
        blog_content="<p>Test content</p>",
        category="tech",
        github_link="https://github.com/test",
    ):
        """Get mock blog data for testing views."""
        return {
            "entry_number": entry_number,
            "template_name": template_name,
            "blog_title": blog_title,
            "blog_content": blog_content,
            "category": category,
            "github_link": github_link,
        }

    @staticmethod
    def get_common_ip_addresses():
        """Get commonly used IP addresses for testing."""
        return {
            "local_ipv4": "127.0.0.1",
            "private_ipv4": "192.168.1.1",
            "public_ipv4": "8.8.8.8",
            "google_dns": "8.8.4.4",
            "ipv6": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        }

    @staticmethod
    def get_common_form_data():
        """Get common form data for testing."""
        return {
            "comment_form": {
                "content": "This is a test comment",
                "author_name": "Test User",
                "author_email": "test@example.com",
                "website": "",  # Honeypot field
            },
            "user_form": {
                "username": "testuser",
                "email": "test@example.com",
                "password1": "testpass123",
                "password2": "testpass123",
            },
        }


class TestDataMixin:
    """Mixin to provide common test data setup for test cases."""

    def setUp_users(self):
        """Set up common users for testing."""
        self.user = UserFactory.create_user()
        self.staff_user = UserFactory.create_staff_user()
        self.superuser = UserFactory.create_superuser()

    def setUp_blog_data(self):
        """Set up common blog data for testing."""
        self.comment_data = {
            "blog_template_name": "0001_test_post",
            "blog_category": "tech",
            "content": "This is a test comment",
            "author": self.user,
        }
        self.mock_blog_data = MockDataFactory.get_mock_blog_data()

    def setUp_photo_data(self):
        """Set up common photo data for testing."""
        self.test_image = PhotoFactory.create_test_image()
        self.test_image_2 = PhotoFactory.create_test_image(color=(0, 255, 0))
