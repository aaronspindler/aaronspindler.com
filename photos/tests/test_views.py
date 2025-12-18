"""
Tests for photo views.

Tests cover:
- album_detail (public/private albums, authentication)
- download_photo functionality
"""

import gc
from io import BytesIO
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image

from accounts.tests.factories import UserFactory
from photos.models import Photo, PhotoAlbum
from photos.tests.factories import PhotoFactory

User = get_user_model()


class AlbumDetailViewTestCase(TestCase):
    """Test cases for album_detail view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create test users
        self.regular_user = UserFactory.create_user(username="regular", password="testpass123")
        self.staff_user = UserFactory.create_staff_user(username="staff", password="testpass123")

        # Create test albums
        self.public_album = PhotoFactory.create_photo_album(
            title="Public Album",
            slug="public-album",
            description="A public album",
            is_private=False,
        )

        self.private_album = PhotoFactory.create_photo_album(
            title="Private Album",
            slug="private-album",
            description="A private album",
            is_private=True,
        )

        # Create test photos
        self.photo1 = self._create_test_photo("Photo 1")
        self.photo2 = self._create_test_photo("Photo 2")

        # Add photos to albums
        self.public_album.photos.add(self.photo1, self.photo2)
        self.private_album.photos.add(self.photo1)

    def _create_test_photo(self, title):
        """Helper to create a test photo with unique image."""
        # Create unique image to avoid duplicate detection
        img = Image.new(
            "RGB",
            (10, 10),
            color=(hash(title) % 256, (hash(title) * 2) % 256, (hash(title) * 3) % 256),
        )
        img_io = BytesIO()
        img.save(img_io, format="JPEG", quality=50)
        img_io.seek(0)

        from django.core.files.uploadedfile import SimpleUploadedFile

        test_image = SimpleUploadedFile(
            name=f"{title.lower().replace(' ', '_')}.jpg",
            content=img_io.getvalue(),
            content_type="image/jpeg",
        )

        photo = Photo(title=title, image=test_image)
        photo.save(skip_duplicate_check=True)
        return photo

    def tearDown(self):
        """Clean up resources after each test."""
        Photo.objects.all().delete()
        PhotoAlbum.objects.all().delete()
        gc.collect()

    def test_public_album_anonymous_access(self):
        """Test anonymous users can access public albums."""
        response = self.client.get(reverse("photos:album_detail", kwargs={"slug": "public-album"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Album")
        self.assertEqual(response.context["album"], self.public_album)
        self.assertEqual(len(response.context["photos"]), 2)

    def test_public_album_authenticated_access(self):
        """Test authenticated users can access public albums."""
        self.client.login(username="regular", password="testpass123")

        response = self.client.get(reverse("photos:album_detail", kwargs={"slug": "public-album"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Album")

    def test_private_album_anonymous_denied(self):
        """Test anonymous users cannot access private albums."""
        response = self.client.get(reverse("photos:album_detail", kwargs={"slug": "private-album"}))

        self.assertEqual(response.status_code, 404)

    def test_private_album_regular_user_denied(self):
        """Test regular authenticated users cannot access private albums."""
        self.client.login(username="regular", password="testpass123")

        response = self.client.get(reverse("photos:album_detail", kwargs={"slug": "private-album"}))

        self.assertEqual(response.status_code, 404)

    def test_private_album_staff_access(self):
        """Test staff users can access private albums."""
        self.client.login(username="staff", password="testpass123")

        response = self.client.get(reverse("photos:album_detail", kwargs={"slug": "private-album"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Private Album")
        self.assertEqual(response.context["album"], self.private_album)

    def test_nonexistent_album(self):
        """Test accessing non-existent album returns 404."""
        response = self.client.get(reverse("photos:album_detail", kwargs={"slug": "does-not-exist"}))

        self.assertEqual(response.status_code, 404)

    def test_photo_ordering_by_date_taken(self):
        """Test photos are ordered by date_taken and created_at."""
        from datetime import datetime, timedelta

        # Update photos with different dates
        self.photo1.date_taken = datetime.now() - timedelta(days=2)
        self.photo1.save()
        self.photo2.date_taken = datetime.now() - timedelta(days=1)
        self.photo2.save()

        response = self.client.get(reverse("photos:album_detail", kwargs={"slug": "public-album"}))

        photos = response.context["photos"]
        # Photos should be ordered newest first
        self.assertEqual(photos[0], self.photo2)
        self.assertEqual(photos[1], self.photo1)

    def test_download_permissions_context(self):
        """Test download permissions are passed to template."""
        self.public_album.allow_downloads = True
        self.public_album.save()

        response = self.client.get(reverse("photos:album_detail", kwargs={"slug": "public-album"}))

        self.assertTrue(response.context["allow_downloads"])

        # Disable downloads
        self.public_album.allow_downloads = False
        self.public_album.save()

        response = self.client.get(reverse("photos:album_detail", kwargs={"slug": "public-album"}))

        self.assertFalse(response.context["allow_downloads"])


class PhotoDetailViewTestCase(TestCase):
    """Test cases for photo_detail view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create test users
        self.regular_user = UserFactory.create_user(username="regular_detail", password="testpass123")
        self.staff_user = UserFactory.create_staff_user(username="staff_detail", password="testpass123")

        # Create test albums
        self.public_album = PhotoFactory.create_photo_album(
            title="Public Album Detail",
            slug="public-album-detail",
            is_private=False,
        )

        self.private_album = PhotoFactory.create_photo_album(
            title="Private Album Detail",
            slug="private-album-detail",
            is_private=True,
        )

        # Create test photos
        self.public_photo = self._create_test_photo("Public Photo")
        self.private_photo = self._create_test_photo("Private Photo")

        # Add photos to albums
        self.public_album.photos.add(self.public_photo)
        self.private_album.photos.add(self.private_photo)

    def _create_test_photo(self, title):
        """Helper to create a test photo with unique image."""
        img = Image.new(
            "RGB",
            (10, 10),
            color=(hash(title) % 256, (hash(title) * 2) % 256, (hash(title) * 3) % 256),
        )
        img_io = BytesIO()
        img.save(img_io, format="JPEG", quality=50)
        img_io.seek(0)

        from django.core.files.uploadedfile import SimpleUploadedFile

        test_image = SimpleUploadedFile(
            name=f"{title.lower().replace(' ', '_')}.jpg",
            content=img_io.getvalue(),
            content_type="image/jpeg",
        )

        photo = Photo(title=title, image=test_image)
        photo.save(skip_duplicate_check=True)
        return photo

    def tearDown(self):
        """Clean up resources after each test."""
        Photo.objects.all().delete()
        PhotoAlbum.objects.all().delete()
        gc.collect()

    def test_public_photo_anonymous_access(self):
        """Test anonymous users can access photos in public albums."""
        response = self.client.get(reverse("photos:photo_detail", kwargs={"pk": self.public_photo.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Photo")
        self.assertEqual(response.context["photo"], self.public_photo)
        self.assertEqual(response.context["album"], self.public_album)

    def test_private_photo_anonymous_denied(self):
        """Test anonymous users cannot access photos in private albums."""
        response = self.client.get(reverse("photos:photo_detail", kwargs={"pk": self.private_photo.pk}))

        self.assertEqual(response.status_code, 404)

    def test_private_photo_staff_access(self):
        """Test staff users can access photos in private albums."""
        self.client.login(username="staff_detail", password="testpass123")

        response = self.client.get(reverse("photos:photo_detail", kwargs={"pk": self.private_photo.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Private Photo")

    def test_private_photo_with_token(self):
        """Test access to private photo with share token."""
        token = str(self.private_album.share_token)
        response = self.client.get(
            reverse("photos:photo_detail", kwargs={"pk": self.private_photo.pk}) + f"?token={token}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Private Photo")

    def test_private_photo_invalid_token(self):
        """Test invalid token is rejected."""
        response = self.client.get(
            reverse("photos:photo_detail", kwargs={"pk": self.private_photo.pk}) + "?token=invalid-token"
        )

        self.assertEqual(response.status_code, 404)

    def test_photo_not_found(self):
        """Test accessing non-existent photo returns 404."""
        response = self.client.get(reverse("photos:photo_detail", kwargs={"pk": 99999}))

        self.assertEqual(response.status_code, 404)

    def test_photo_detail_context_data(self):
        """Test photo detail view provides correct context."""
        response = self.client.get(reverse("photos:photo_detail", kwargs={"pk": self.public_photo.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertIn("photo", response.context)
        self.assertIn("album", response.context)
        self.assertIn("albums", response.context)
        self.assertIn("structured_data", response.context)
        self.assertIn("page_og_title", response.context)

    def test_photo_navigation_context(self):
        """Test prev/next photo navigation is provided."""
        # Add more photos to test navigation
        photo2 = self._create_test_photo("Public Photo 2")
        photo3 = self._create_test_photo("Public Photo 3")
        self.public_album.photos.add(photo2, photo3)

        # Get the middle photo
        response = self.client.get(reverse("photos:photo_detail", kwargs={"pk": photo2.pk}))

        self.assertEqual(response.status_code, 200)
        # prev_photo and next_photo depend on ordering, just check they exist in context
        self.assertIn("prev_photo", response.context)
        self.assertIn("next_photo", response.context)

    def test_seo_meta_tags_present(self):
        """Test SEO meta tags are present in response."""
        response = self.client.get(reverse("photos:photo_detail", kwargs={"pk": self.public_photo.pk}))

        self.assertEqual(response.status_code, 200)
        # Check for structured data script tag
        self.assertContains(response, 'application/ld+json')
        self.assertContains(response, 'schema.org')

    def test_get_absolute_url(self):
        """Test Photo model get_absolute_url method."""
        url = self.public_photo.get_absolute_url()
        expected = reverse("photos:photo_detail", kwargs={"pk": self.public_photo.pk})
        self.assertEqual(url, expected)


class DownloadPhotoViewTestCase(TestCase):
    """Test cases for download_photo view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create staff user
        self.staff_user = UserFactory.create_staff_user(username="staff", password="testpass123")

        # Create album and photo
        self.album = PhotoFactory.create_photo_album(
            title="Test Album",
            slug="test-album",
            is_private=False,
            allow_downloads=True,
        )

        self.photo = self._create_test_photo("Test Photo")
        self.album.photos.add(self.photo)

    def _create_test_photo(self, title):
        """Helper to create a test photo."""
        return PhotoFactory.create_photo(title=title, original_filename=f"{title}.jpg")

    @patch("requests.get")
    def test_download_photo_success(self, mock_get):
        """Test successful photo download."""
        # Mock S3 response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"image_content"
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_get.return_value = mock_response

        # Mock image URL
        with patch.object(self.photo, "get_image_url", return_value="http://s3.example.com/photo.jpg"):
            response = self.client.get(
                reverse(
                    "photos:download_photo",
                    kwargs={"slug": "test-album", "photo_id": self.photo.id},
                )
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(".jpg", response["Content-Disposition"])  # Should contain some jpg filename

    def test_download_photo_album_not_found(self):
        """Test download from non-existent album."""
        response = self.client.get(
            reverse(
                "photos:download_photo",
                kwargs={"slug": "nonexistent", "photo_id": self.photo.id},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_download_photo_not_in_album(self):
        """Test downloading photo not in the specified album."""
        other_photo = self._create_test_photo("Other Photo")

        response = self.client.get(
            reverse(
                "photos:download_photo",
                kwargs={"slug": "test-album", "photo_id": other_photo.id},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_download_disabled(self):
        """Test download when album downloads are disabled."""
        self.album.allow_downloads = False
        self.album.save()

        response = self.client.get(
            reverse(
                "photos:download_photo",
                kwargs={"slug": "test-album", "photo_id": self.photo.id},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_download_private_album_anonymous(self):
        """Test anonymous user cannot download from private album."""
        self.album.is_private = True
        self.album.save()

        response = self.client.get(
            reverse(
                "photos:download_photo",
                kwargs={"slug": "test-album", "photo_id": self.photo.id},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_download_private_album_staff(self):
        """Test staff can download from private album."""
        self.album.is_private = True
        self.album.save()
        self.client.login(username="staff", password="testpass123")

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"image_content"
            mock_response.headers = {"content-type": "image/jpeg"}
            mock_get.return_value = mock_response

            with patch.object(
                self.photo,
                "get_image_url",
                return_value="http://s3.example.com/photo.jpg",
            ):
                response = self.client.get(
                    reverse(
                        "photos:download_photo",
                        kwargs={"slug": "test-album", "photo_id": self.photo.id},
                    )
                )

        self.assertEqual(response.status_code, 200)

    @patch("requests.get")
    def test_download_photo_s3_error(self, mock_get):
        """Test handling S3 download errors."""
        # Mock S3 error response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        with patch.object(self.photo, "get_image_url", return_value="http://s3.example.com/photo.jpg"):
            response = self.client.get(
                reverse(
                    "photos:download_photo",
                    kwargs={"slug": "test-album", "photo_id": self.photo.id},
                )
            )

        self.assertEqual(response.status_code, 404)

    @patch("requests.get")
    def test_download_photo_network_error(self, mock_get):
        """Test handling network errors during download."""
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        with patch.object(self.photo, "get_image_url", return_value="http://s3.example.com/photo.jpg"):
            response = self.client.get(
                reverse(
                    "photos:download_photo",
                    kwargs={"slug": "test-album", "photo_id": self.photo.id},
                )
            )

        self.assertEqual(response.status_code, 404)
