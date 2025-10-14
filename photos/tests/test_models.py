"""
Tests for Photo and PhotoAlbum models.

Tests cover:
- Photo save() with image processing and duplicate detection
- PhotoAlbum slug generation and download URL methods
- get_similar_images() functionality
- Model field validations
"""

import gc
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from PIL import Image

from photos.models import Photo, PhotoAlbum


class PhotoModelTestCase(TestCase):
    """Test cases for the Photo model."""

    def setUp(self):
        """Set up test data."""
        # Create a test image
        self.test_image = self._create_test_image()
        self.test_image_2 = self._create_test_image(color=(0, 255, 0))

    def tearDown(self):
        """Clean up resources after each test."""
        Photo.objects.all().delete()
        PhotoAlbum.objects.all().delete()
        gc.collect()

    def _create_test_image(self, size=(10, 10), color=(255, 0, 0), format="JPEG"):
        """Helper to create a test image."""
        img = Image.new("RGB", size, color)
        img_io = BytesIO()
        img.save(img_io, format=format, quality=50)
        img_io.seek(0)
        return SimpleUploadedFile(name="test.jpg", content=img_io.getvalue(), content_type="image/jpeg")

    def test_photo_creation_basic(self):
        """Test basic photo creation."""
        photo = Photo.objects.create(title="Test Photo", description="Test Description", image=self.test_image)

        self.assertEqual(photo.title, "Test Photo")
        self.assertEqual(photo.description, "Test Description")
        self.assertIsNotNone(photo.image)
        self.assertIsNotNone(photo.pk)

    @patch("photos.models.ImageOptimizer.process_uploaded_image")
    @patch("photos.models.ExifExtractor.extract_exif")
    @patch("photos.models.ImageMetadataExtractor.extract_basic_metadata")
    @patch("photos.models.DuplicateDetector.compute_and_store_hashes")
    def test_photo_save_processes_image(self, mock_hashes, mock_metadata, mock_exif, mock_process):
        """Test that save() triggers image processing."""
        # Setup mocks
        mock_hashes.return_value = {
            "file_hash": "testhash123",
            "perceptual_hash": "perceptualhash456",
        }
        mock_metadata.return_value = {
            "width": 10,
            "height": 10,
            "file_size": 1024,
            "format": "JPEG",
            "mode": "RGB",
        }
        mock_exif.return_value = {
            "camera_make": "Canon",
            "camera_model": "EOS R5",
            "iso": 400,
            "aperture": "f/2.8",
            "shutter_speed": "1/250",
            "focal_length": "50mm",
            "date_taken": datetime(2024, 1, 1, 12, 0, 0),
            "full_exif": {"Make": "Canon", "Model": "EOS R5"},
        }

        mock_optimized = Mock()
        mock_optimized.name = "test_optimized.jpg"
        mock_display = Mock()
        mock_display.name = "test_display.jpg"

        mock_process.return_value = (
            {"optimized": mock_optimized, "display": mock_display},
            (0.5, 0.5),  # focal point
        )

        # Create photo with skip_duplicate_check to avoid duplicate check but still process image
        photo = Photo(title="Test", image=self.test_image)
        photo.save(skip_duplicate_check=True)

        # Verify processing was called (hashes are computed in _process_image regardless of skip_duplicate_check)
        mock_hashes.assert_called_once()
        mock_metadata.assert_called_once()
        mock_exif.assert_called_once()
        mock_process.assert_called_once()

        # Verify metadata was set
        self.assertEqual(photo.file_hash, "testhash123")
        self.assertEqual(photo.perceptual_hash, "perceptualhash456")
        self.assertEqual(photo.width, 10)
        self.assertEqual(photo.height, 10)
        self.assertEqual(photo.file_size, 1024)
        self.assertEqual(photo.camera_make, "Canon")
        self.assertEqual(photo.camera_model, "EOS R5")
        self.assertEqual(photo.focal_point_x, 0.5)
        self.assertEqual(photo.focal_point_y, 0.5)

    @patch("photos.models.DuplicateDetector.find_duplicates")
    def test_photo_duplicate_detection_raises_error(self, mock_find_duplicates):
        """Test that duplicate detection raises ValidationError for exact duplicates."""
        # Create existing photo with skip_duplicate_check to avoid issues
        existing_photo = Photo(title="Existing Photo", image=self.test_image, file_hash="existinghash")
        existing_photo.save(skip_duplicate_check=True)

        # Setup mock to return exact duplicate
        mock_find_duplicates.return_value = {
            "exact_duplicates": [existing_photo],
            "similar_images": [],
            "file_hash": "existinghash",
            "perceptual_hash": "perceptualhash",
        }

        # Try to save duplicate - should raise ValidationError
        with self.assertRaises(ValidationError) as context:
            photo = Photo(title="Duplicate", image=self.test_image_2)
            photo.save()

        self.assertIn("exact duplicate", str(context.exception).lower())

    @patch("photos.models.DuplicateDetector.find_duplicates")
    def test_photo_skip_duplicate_check(self, mock_find_duplicates):
        """Test that duplicate check can be skipped."""
        # Setup mock to return exact duplicate
        existing_photo = Photo(title="Existing Photo", image=self.test_image, file_hash="existinghash")
        existing_photo.save(skip_duplicate_check=True)

        mock_find_duplicates.return_value = {
            "exact_duplicates": [existing_photo],
            "similar_images": [],
            "file_hash": "existinghash",
            "perceptual_hash": "perceptualhash",
        }

        # Save with skip_duplicate_check=True should not raise error
        photo = Photo(title="Duplicate", image=self.test_image_2)
        photo.save(skip_duplicate_check=True)

        # Verify duplicate check was not called
        mock_find_duplicates.assert_not_called()
        self.assertIsNotNone(photo.pk)

    def test_photo_str_representation(self):
        """Test string representation of Photo."""
        # With title
        photo1 = Photo(title="My Photo", pk=1)
        self.assertEqual(str(photo1), "My Photo")

        # Without title but with filename
        photo2 = Photo(original_filename="DSC_001.jpg", pk=2)
        self.assertEqual(str(photo2), "DSC_001.jpg")

        # Without title or filename
        photo3 = Photo(pk=3)
        self.assertEqual(str(photo3), "Photo 3")

    @patch("photos.models.Photo.objects")
    def test_get_similar_images(self, mock_objects):
        """Test finding similar images."""
        # Create test photos
        photo1 = Photo(pk=1, title="Photo 1", perceptual_hash="hash1")
        photo2 = Photo(pk=2, title="Photo 2", perceptual_hash="hash2")
        photo3 = Photo(pk=3, title="Photo 3", perceptual_hash="hash3")

        # Mock the queryset to return only our test photos
        mock_qs = Mock()
        mock_qs.exclude.return_value = mock_qs
        mock_qs.__iter__ = Mock(return_value=iter([photo2, photo3]))

        mock_objects.exclude.return_value = mock_qs

        # Mock the DuplicateDetector.compare_hashes
        with patch("photos.models.DuplicateDetector.compare_hashes") as mock_compare:
            # Setup mock comparisons
            def compare_side_effect(hash1, hash2, threshold=5):
                if hash1 == "hash1" and hash2 == "hash2":
                    return True, 3  # Similar with distance 3
                elif hash1 == "hash1" and hash2 == "hash3":
                    return True, 4  # Similar with distance 4
                return False, 10

            mock_compare.side_effect = compare_side_effect

            # Get similar images
            similar = photo1.get_similar_images(threshold=5)

            # Verify results are sorted by distance
            self.assertEqual(len(similar), 2)
            self.assertEqual(similar[0][0], photo2)
            self.assertEqual(similar[0][1], 3)
            self.assertEqual(similar[1][0], photo3)
            self.assertEqual(similar[1][1], 4)

    def test_get_image_url_different_sizes(self):
        """Test getting URLs for different image sizes."""
        photo = Photo()
        photo.image = Mock()
        photo.image.url = "http://example.com/original.jpg"
        photo.image_optimized = Mock()
        photo.image_optimized.url = "http://example.com/optimized.jpg"
        photo.image_display = Mock()
        photo.image_display.url = "http://example.com/display.jpg"

        # Test different sizes
        self.assertEqual(photo.get_image_url("display"), "http://example.com/display.jpg")
        self.assertEqual(photo.get_image_url("optimized"), "http://example.com/optimized.jpg")
        self.assertEqual(photo.get_image_url("original"), "http://example.com/original.jpg")

        # Test fallback
        self.assertEqual(photo.get_image_url("invalid"), "http://example.com/display.jpg")

    def test_get_image_url_missing_files(self):
        """Test get_image_url when files are missing."""
        photo = Photo()

        # No images at all
        self.assertIsNone(photo.get_image_url("display"))

        # Only original exists
        photo.image = Mock()
        photo.image.url = "http://example.com/original.jpg"
        self.assertEqual(photo.get_image_url("display"), "http://example.com/original.jpg")

    @patch("photos.models.ExifExtractor.extract_exif")
    def test_exif_extraction(self, mock_extract):
        """Test EXIF data extraction and storage."""
        mock_extract.return_value = {
            "camera_make": "Nikon",
            "camera_model": "D850",
            "lens_model": "NIKKOR 24-70mm f/2.8",
            "iso": 200,
            "aperture": "f/4.0",
            "shutter_speed": "1/500",
            "focal_length": "35mm",
            "date_taken": datetime(2024, 3, 15, 14, 30, 0),
            "gps_latitude": Decimal("40.7128"),
            "gps_longitude": Decimal("-74.0060"),
            "gps_altitude": Decimal("10.5"),
            "full_exif": {"Make": "Nikon"},
        }

        photo = Photo(image=self.test_image)
        photo.save()

        # Verify EXIF fields were populated
        self.assertEqual(photo.camera_make, "Nikon")
        self.assertEqual(photo.camera_model, "D850")
        self.assertEqual(photo.lens_model, "NIKKOR 24-70mm f/2.8")
        self.assertEqual(photo.iso, 200)
        self.assertEqual(photo.aperture, "f/4.0")
        self.assertEqual(photo.shutter_speed, "1/500")
        self.assertEqual(photo.focal_length, "35mm")
        self.assertEqual(photo.date_taken, datetime(2024, 3, 15, 14, 30, 0))
        self.assertEqual(photo.gps_latitude, Decimal("40.7128"))
        self.assertEqual(photo.gps_longitude, Decimal("-74.0060"))
        self.assertEqual(photo.gps_altitude, Decimal("10.5"))


class PhotoAlbumModelTestCase(TestCase):
    """Test cases for the PhotoAlbum model."""

    def setUp(self):
        """Set up test data."""
        self.test_image = self._create_test_image()

    def _create_test_image(self, size=(10, 10), color=(255, 0, 0), format="JPEG"):
        """Helper to create a test image."""
        img = Image.new("RGB", size, color)
        img_io = BytesIO()
        img.save(img_io, format=format, quality=50)
        img_io.seek(0)
        return SimpleUploadedFile(name="test.jpg", content=img_io.getvalue(), content_type="image/jpeg")

    def test_album_creation(self):
        """Test basic album creation."""
        album = PhotoAlbum.objects.create(
            title="Test Album",
            description="Test Description",
            is_private=False,
            allow_downloads=True,
        )

        self.assertEqual(album.title, "Test Album")
        self.assertEqual(album.description, "Test Description")
        self.assertFalse(album.is_private)
        self.assertTrue(album.allow_downloads)
        self.assertIsNotNone(album.created_at)
        self.assertIsNotNone(album.updated_at)

    def test_slug_generation(self):
        """Test automatic slug generation from title."""
        album = PhotoAlbum.objects.create(title="My Vacation Photos 2024!")

        self.assertEqual(album.slug, "my-vacation-photos-2024")

    def test_slug_uniqueness(self):
        """Test that slugs are made unique when conflicts occur."""
        # Create first album
        album1 = PhotoAlbum.objects.create(title="Test Album")
        self.assertEqual(album1.slug, "test-album")

        # Create second album with same title
        album2 = PhotoAlbum.objects.create(title="Test Album")
        self.assertEqual(album2.slug, "test-album-1")

        # Create third album with same title
        album3 = PhotoAlbum.objects.create(title="Test Album")
        self.assertEqual(album3.slug, "test-album-2")

    def test_custom_slug_preserved(self):
        """Test that custom slugs are preserved."""
        album = PhotoAlbum.objects.create(title="Test Album", slug="custom-slug")

        self.assertEqual(album.slug, "custom-slug")

    def test_album_str_representation(self):
        """Test string representation of PhotoAlbum."""
        # With title
        album1 = PhotoAlbum(title="My Album", pk=1)
        self.assertEqual(str(album1), "My Album")

        # Without title
        album2 = PhotoAlbum(pk=2)
        self.assertEqual(str(album2), "Album 2")

    def test_album_photo_relationship(self):
        """Test many-to-many relationship with photos."""
        # Create album and photos
        album = PhotoAlbum.objects.create(title="Test Album")
        photo1 = Photo(title="Photo 1", image=self.test_image)
        photo1.save(skip_duplicate_check=True)

        # Use different image for photo2 to avoid duplicate detection
        test_image_2 = self._create_test_image(color=(0, 255, 0))
        photo2 = Photo(title="Photo 2", image=test_image_2)
        photo2.save(skip_duplicate_check=True)

        # Add photos to album
        album.photos.add(photo1, photo2)

        # Verify relationship
        self.assertEqual(album.photos.count(), 2)
        self.assertIn(photo1, album.photos.all())
        self.assertIn(photo2, album.photos.all())

        # Verify reverse relationship
        self.assertIn(album, photo1.albums.all())
        self.assertIn(album, photo2.albums.all())

    def test_get_download_url(self):
        """Test getting download URLs for album zips."""
        album = PhotoAlbum(allow_downloads=True)

        # Setup mock files with URL property
        mock_zip_original = Mock()
        mock_zip_original.name = "test.zip"
        mock_zip_original.url = "http://example.com/original.zip"

        mock_zip_optimized = Mock()
        mock_zip_optimized.name = "test_optimized.zip"
        mock_zip_optimized.url = "http://example.com/optimized.zip"

        # Assign mocked files to album
        album.zip_file = mock_zip_original
        album.zip_file_optimized = mock_zip_optimized

        # Test when downloads allowed
        self.assertEqual(album.get_download_url("original"), "http://example.com/original.zip")
        self.assertEqual(album.get_download_url("optimized"), "http://example.com/optimized.zip")

        # Test default quality
        self.assertEqual(album.get_download_url(), "http://example.com/optimized.zip")

        # Test when downloads not allowed
        album.allow_downloads = False
        self.assertIsNone(album.get_download_url("original"))
        self.assertIsNone(album.get_download_url("optimized"))

    def test_get_download_url_no_files(self):
        """Test get_download_url when zip files don't exist."""
        album = PhotoAlbum(allow_downloads=True)
        album.zip_file = None
        album.zip_file_optimized = None

        self.assertIsNone(album.get_download_url("original"))
        self.assertIsNone(album.get_download_url("optimized"))

    @patch("photos.tasks.generate_album_zip.delay")
    def test_regenerate_zip_files_async(self, mock_task):
        """Test regenerating zip files asynchronously."""
        album = PhotoAlbum.objects.create(title="Test Album")

        album.regenerate_zip_files(async_task=True)
        mock_task.assert_called_once_with(album.pk)

    @patch("photos.tasks.generate_album_zip")
    def test_regenerate_zip_files_sync(self, mock_task):
        """Test regenerating zip files synchronously."""
        album = PhotoAlbum.objects.create(title="Test Album")
        mock_task.return_value = True

        result = album.regenerate_zip_files(async_task=False)

        mock_task.assert_called_once_with(album.pk)
        self.assertTrue(result)

    def test_album_privacy_settings(self):
        """Test album privacy settings."""
        # Public album
        public_album = PhotoAlbum.objects.create(title="Public Album", is_private=False)
        self.assertFalse(public_album.is_private)

        # Private album
        private_album = PhotoAlbum.objects.create(title="Private Album", is_private=True)
        self.assertTrue(private_album.is_private)

    def test_album_download_settings(self):
        """Test album download settings."""
        # Downloads disabled by default
        album1 = PhotoAlbum.objects.create(title="Album 1")
        self.assertFalse(album1.allow_downloads)

        # Downloads enabled
        album2 = PhotoAlbum.objects.create(title="Album 2", allow_downloads=True)
        self.assertTrue(album2.allow_downloads)

    def test_album_zip_file_storage(self):
        """Test that zip files use private storage."""
        album = PhotoAlbum.objects.create(title="Test Album")

        # Check that the field uses private storage
        self.assertEqual(album.zip_file.storage.__class__.__name__, "PrivateMediaStorage")
        self.assertEqual(album.zip_file_optimized.storage.__class__.__name__, "PrivateMediaStorage")

        # Check upload paths
        self.assertEqual(album.zip_file.field.upload_to, "albums/zips/original/")
        self.assertEqual(album.zip_file_optimized.field.upload_to, "albums/zips/optimized/")
