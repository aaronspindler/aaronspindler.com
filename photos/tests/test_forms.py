"""
Tests for photo forms.

Tests cover:
- PhotoBulkUploadForm multiple file upload handling
- Duplicate detection during bulk upload
- Error handling
- MultipleFileInput and MultipleFileField widgets
"""

from io import BytesIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from photos.forms import MultipleFileField, MultipleFileInput, PhotoBulkUploadForm
from photos.models import Photo
from tests.factories import PhotoFactory


class MultipleFileInputTestCase(TestCase):
    """Test cases for MultipleFileInput widget."""

    def test_multiple_file_input_allows_multiple(self):
        """Test that MultipleFileInput allows multiple file selection."""
        widget = MultipleFileInput()
        self.assertTrue(widget.allow_multiple_selected)


class MultipleFileFieldTestCase(TestCase):
    """Test cases for MultipleFileField."""

    def test_multiple_file_field_default_widget(self):
        """Test that MultipleFileField uses MultipleFileInput by default."""
        field = MultipleFileField()
        self.assertIsInstance(field.widget, MultipleFileInput)

    def test_clean_single_file(self):
        """Test cleaning a single file."""
        field = MultipleFileField(required=False)

        # Create a test file
        test_file = SimpleUploadedFile(name="test.jpg", content=b"test content", content_type="image/jpeg")

        result = field.clean(test_file)
        self.assertEqual(result, test_file)

    def test_clean_multiple_files(self):
        """Test cleaning multiple files."""
        field = MultipleFileField(required=False)

        # Create test files
        file1 = SimpleUploadedFile("test1.jpg", b"content1", "image/jpeg")
        file2 = SimpleUploadedFile("test2.jpg", b"content2", "image/jpeg")
        files = [file1, file2]

        result = field.clean(files)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "test1.jpg")
        self.assertEqual(result[1].name, "test2.jpg")

    def test_clean_empty_list(self):
        """Test cleaning empty list when field is not required."""
        field = MultipleFileField(required=False)
        result = field.clean([])
        self.assertEqual(result, [])

    def test_clean_required_field_empty(self):
        """Test that required field raises error when empty."""
        field = MultipleFileField(required=True)

        with self.assertRaises(ValidationError):
            field.clean(None)


class PhotoBulkUploadFormTestCase(TestCase):
    """Test cases for PhotoBulkUploadForm."""

    def setUp(self):
        """Set up test data."""
        # Create test albums
        self.album1 = PhotoFactory.create_photo_album(title="Album 1", slug="album-1")
        self.album2 = PhotoFactory.create_photo_album(title="Album 2", slug="album-2")

    def _create_test_image_file(self, name="test.jpg", color=(255, 0, 0)):
        """Helper to create a test image file."""
        img = Image.new("RGB", (100, 100), color=color)
        img_io = BytesIO()
        img.save(img_io, format="JPEG")
        img_io.seek(0)
        return SimpleUploadedFile(name=name, content=img_io.getvalue(), content_type="image/jpeg")

    def test_form_initialization(self):
        """Test form initialization and field setup."""
        form = PhotoBulkUploadForm()

        # Check fields exist
        self.assertIn("images", form.fields)
        self.assertIn("album", form.fields)

        # Check images field is required
        self.assertTrue(form.fields["images"].required)

        # Check album field is optional
        self.assertFalse(form.fields["album"].required)

        # Check album queryset
        album_queryset = form.fields["album"].queryset
        self.assertIn(self.album1, album_queryset)
        self.assertIn(self.album2, album_queryset)

    def test_form_valid_single_image(self):
        """Test form validation with a single image."""
        image_file = self._create_test_image_file("single.jpg")

        form = PhotoBulkUploadForm(files={"images": image_file})

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["images"], image_file)

    def test_form_valid_multiple_images(self):
        """Test form validation with multiple images."""
        image1 = self._create_test_image_file("image1.jpg")
        image2 = self._create_test_image_file("image2.jpg")

        form = PhotoBulkUploadForm(files={"images": [image1, image2]})

        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.cleaned_data["images"]), 2)

    def test_form_with_album_selection(self):
        """Test form with album selection."""
        image_file = self._create_test_image_file()

        form = PhotoBulkUploadForm(data={"album": self.album1.pk}, files={"images": image_file})

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["album"], self.album1)

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_single_image_success(self, mock_find_duplicates):
        """Test saving a single uploaded image."""
        # Setup mock - no duplicates found
        mock_find_duplicates.return_value = {
            "exact_duplicates": [],
            "similar_images": [],
            "file_hash": "hash123",
            "perceptual_hash": "phash456",
        }

        image_file = self._create_test_image_file()
        form = PhotoBulkUploadForm(files={"images": image_file})

        self.assertTrue(form.is_valid())
        result = form.save()

        # Check result structure
        self.assertIn("created", result)
        self.assertIn("skipped", result)
        self.assertIn("errors", result)

        # One photo should be created
        self.assertEqual(len(result["created"]), 1)
        self.assertEqual(len(result["skipped"]), 0)
        self.assertEqual(len(result["errors"]), 0)

        # Verify photo was created
        photo = result["created"][0]
        self.assertIsInstance(photo, Photo)
        self.assertEqual(photo.file_hash, "hash123")
        self.assertEqual(photo.perceptual_hash, "phash456")

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_multiple_images_success(self, mock_find_duplicates):
        """Test saving multiple uploaded images."""
        # Setup mock - no duplicates
        mock_find_duplicates.return_value = {
            "exact_duplicates": [],
            "similar_images": [],
            "file_hash": "hash123",
            "perceptual_hash": "phash456",
        }

        image1 = self._create_test_image_file("image1.jpg")
        image2 = self._create_test_image_file("image2.jpg")

        form = PhotoBulkUploadForm(files={"images": [image1, image2]})

        self.assertTrue(form.is_valid())
        result = form.save()

        # Two photos should be created
        self.assertEqual(len(result["created"]), 2)
        self.assertEqual(len(result["skipped"]), 0)
        self.assertEqual(len(result["errors"]), 0)

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_with_album_assignment(self, mock_find_duplicates):
        """Test saving images with album assignment."""
        mock_find_duplicates.return_value = {
            "exact_duplicates": [],
            "similar_images": [],
            "file_hash": "hash123",
            "perceptual_hash": "phash456",
        }

        image_file = self._create_test_image_file()
        form = PhotoBulkUploadForm(data={"album": self.album1.pk}, files={"images": image_file})

        self.assertTrue(form.is_valid())
        result = form.save()

        # Verify photo was added to album
        photo = result["created"][0]
        self.assertIn(self.album1, photo.albums.all())
        self.assertEqual(self.album1.photos.count(), 1)

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_skip_exact_duplicate(self, mock_find_duplicates):
        """Test that exact duplicates are skipped by default."""
        # Create existing photo
        existing_photo = PhotoFactory.create_photo(title="Existing Photo", file_hash="existing_hash")

        # Setup mock - exact duplicate found
        mock_find_duplicates.return_value = {
            "exact_duplicates": [existing_photo],
            "similar_images": [],
            "file_hash": "existing_hash",
            "perceptual_hash": "phash123",
        }

        image_file = self._create_test_image_file()
        form = PhotoBulkUploadForm(files={"images": image_file})

        self.assertTrue(form.is_valid())
        result = form.save(skip_duplicates=True)

        # Photo should be skipped
        self.assertEqual(len(result["created"]), 0)
        self.assertEqual(len(result["skipped"]), 1)
        self.assertEqual(len(result["errors"]), 0)

        # Check skip reason
        filename, reason = result["skipped"][0]
        self.assertEqual(filename, "test.jpg")
        self.assertIn("Exact duplicate", reason)
        self.assertIn(str(existing_photo), reason)

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_raise_on_duplicate(self, mock_find_duplicates):
        """Test that duplicates raise error when skip_duplicates=False."""
        existing_photo = PhotoFactory.create_photo(title="Existing Photo", file_hash="existing_hash")

        mock_find_duplicates.return_value = {
            "exact_duplicates": [existing_photo],
            "similar_images": [],
            "file_hash": "existing_hash",
            "perceptual_hash": "phash123",
        }

        image_file = self._create_test_image_file()
        form = PhotoBulkUploadForm(files={"images": image_file})

        self.assertTrue(form.is_valid())
        result = form.save(skip_duplicates=False)

        # Should have error instead of skip
        self.assertEqual(len(result["created"]), 0)
        self.assertEqual(len(result["skipped"]), 0)
        self.assertEqual(len(result["errors"]), 1)

        # Check error
        filename, error = result["errors"][0]
        self.assertEqual(filename, "test.jpg")
        self.assertIn("Exact duplicate", error)

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_with_similar_images(self, mock_find_duplicates):
        """Test saving when similar images are detected."""
        # Create existing similar photo
        similar_photo = PhotoFactory.create_photo(title="Similar Photo", perceptual_hash="similar_hash")

        # Setup mock - similar image found but not exact
        mock_find_duplicates.return_value = {
            "exact_duplicates": [],
            "similar_images": [(similar_photo, 3)],  # distance of 3
            "file_hash": "new_hash",
            "perceptual_hash": "new_phash",
        }

        image_file = self._create_test_image_file()
        form = PhotoBulkUploadForm(files={"images": image_file})

        self.assertTrue(form.is_valid())
        result = form.save()

        # Similar images should not prevent upload
        self.assertEqual(len(result["created"]), 1)
        self.assertEqual(len(result["skipped"]), 0)
        self.assertEqual(len(result["errors"]), 0)

    @patch("photos.models.Photo.save")
    def test_save_handles_exceptions(self, mock_save):
        """Test that save handles exceptions gracefully."""
        # Make save raise an exception
        mock_save.side_effect = Exception("Database error")

        image_file = self._create_test_image_file()
        form = PhotoBulkUploadForm(files={"images": image_file})

        self.assertTrue(form.is_valid())

        with patch("photos.forms.DuplicateDetector.find_duplicates") as mock_find:
            mock_find.return_value = {
                "exact_duplicates": [],
                "similar_images": [],
                "file_hash": "hash",
                "perceptual_hash": "phash",
            }

            result = form.save()

        # Should have error
        self.assertEqual(len(result["created"]), 0)
        self.assertEqual(len(result["errors"]), 1)

        filename, error = result["errors"][0]
        self.assertEqual(filename, "test.jpg")
        self.assertIn("Database error", error)

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_mixed_results(self, mock_find_duplicates):
        """Test saving multiple images with mixed results."""
        # Create existing photo for duplicate
        existing = PhotoFactory.create_photo(title="Existing", file_hash="existing_hash")

        # Setup mock to return different results for each call
        def find_duplicates_side_effect(image_file, existing_photos, **kwargs):
            # Check filename to determine which image is being processed
            if hasattr(image_file, "name"):
                if "duplicate" in image_file.name:
                    return {
                        "exact_duplicates": [existing],
                        "similar_images": [],
                        "file_hash": "existing_hash",
                        "perceptual_hash": "phash",
                    }
                elif "error" in image_file.name:
                    raise Exception("Processing error")

            return {
                "exact_duplicates": [],
                "similar_images": [],
                "file_hash": "new_hash",
                "perceptual_hash": "new_phash",
            }

        mock_find_duplicates.side_effect = find_duplicates_side_effect

        # Create test images
        image1 = self._create_test_image_file("success.jpg")
        image2 = self._create_test_image_file("duplicate.jpg")
        image3 = self._create_test_image_file("error.jpg")

        form = PhotoBulkUploadForm(files={"images": [image1, image2, image3]})

        self.assertTrue(form.is_valid())
        result = form.save()

        # Check mixed results
        self.assertEqual(len(result["created"]), 1)  # Only success.jpg
        self.assertEqual(len(result["skipped"]), 1)  # duplicate.jpg
        self.assertEqual(len(result["errors"]), 1)  # error.jpg

    def test_form_invalid_no_images(self):
        """Test form is invalid without images."""
        form = PhotoBulkUploadForm(data={}, files={})
        self.assertFalse(form.is_valid())
        self.assertIn("images", form.errors)

    def test_form_help_text(self):
        """Test form field help text."""
        form = PhotoBulkUploadForm()

        self.assertEqual(form.fields["images"].help_text, "You can select multiple images at once")
        self.assertEqual(
            form.fields["album"].help_text,
            "Optional: Add all uploaded photos to this album",
        )

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_preserves_hashes(self, mock_find_duplicates):
        """Test that computed hashes are preserved to avoid recomputation."""
        mock_find_duplicates.return_value = {
            "exact_duplicates": [],
            "similar_images": [],
            "file_hash": "computed_file_hash",
            "perceptual_hash": "computed_perceptual_hash",
        }

        image_file = self._create_test_image_file()
        form = PhotoBulkUploadForm(files={"images": image_file})

        self.assertTrue(form.is_valid())

        # Mock Photo.save to verify skip_duplicate_check is True
        with patch.object(Photo, "save") as mock_save:
            result = form.save()

            # Verify save was called with skip_duplicate_check=True
            mock_save.assert_called_once_with(skip_duplicate_check=True)

        # Verify hashes were set on the photo
        photo = result["created"][0]
        self.assertEqual(photo.file_hash, "computed_file_hash")
        self.assertEqual(photo.perceptual_hash, "computed_perceptual_hash")
