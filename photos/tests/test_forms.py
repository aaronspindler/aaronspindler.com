from io import BytesIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from photos.forms import MultipleFileField, MultipleFileInput, PhotoBulkUploadForm
from photos.models import Photo
from photos.tests.factories import PhotoFactory


class MultipleFileInputTestCase(TestCase):
    def test_multiple_file_input_allows_multiple(self):
        widget = MultipleFileInput()
        self.assertTrue(widget.allow_multiple_selected)


class MultipleFileFieldTestCase(TestCase):
    def test_multiple_file_field_default_widget(self):
        field = MultipleFileField()
        self.assertIsInstance(field.widget, MultipleFileInput)

    def test_clean_single_file(self):
        field = MultipleFileField(required=False)

        test_file = SimpleUploadedFile(name="test.jpg", content=b"test content", content_type="image/jpeg")

        result = field.clean(test_file)
        self.assertEqual(result, test_file)

    def test_clean_multiple_files(self):
        field = MultipleFileField(required=False)

        file1 = SimpleUploadedFile("test1.jpg", b"content1", "image/jpeg")
        file2 = SimpleUploadedFile("test2.jpg", b"content2", "image/jpeg")
        files = [file1, file2]

        result = field.clean(files)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "test1.jpg")
        self.assertEqual(result[1].name, "test2.jpg")

    def test_clean_empty_list(self):
        field = MultipleFileField(required=False)
        result = field.clean([])
        self.assertEqual(result, [])

    def test_clean_required_field_empty(self):
        field = MultipleFileField(required=True)

        with self.assertRaises(ValidationError):
            field.clean(None)


class PhotoBulkUploadFormTestCase(TestCase):
    def setUp(self):
        self.album1 = PhotoFactory.create_photo_album(title="Album 1", slug="album-1")
        self.album2 = PhotoFactory.create_photo_album(title="Album 2", slug="album-2")

    def _create_test_image_file(self, name="test.jpg", color=(255, 0, 0)):
        img = Image.new("RGB", (100, 100), color=color)
        img_io = BytesIO()
        img.save(img_io, format="JPEG")
        img_io.seek(0)
        return SimpleUploadedFile(name=name, content=img_io.getvalue(), content_type="image/jpeg")

    def test_form_initialization(self):
        form = PhotoBulkUploadForm()

        self.assertIn("images", form.fields)
        self.assertIn("album", form.fields)

        self.assertTrue(form.fields["images"].required)

        self.assertFalse(form.fields["album"].required)

        album_queryset = form.fields["album"].queryset
        self.assertIn(self.album1, album_queryset)
        self.assertIn(self.album2, album_queryset)

    def test_form_valid_single_image(self):
        image_file = self._create_test_image_file("single.jpg")

        form = PhotoBulkUploadForm(files={"images": image_file})

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["images"], image_file)

    def test_form_valid_multiple_images(self):
        image1 = self._create_test_image_file("image1.jpg")
        image2 = self._create_test_image_file("image2.jpg")

        form = PhotoBulkUploadForm(files={"images": [image1, image2]})

        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.cleaned_data["images"]), 2)

    def test_form_with_album_selection(self):
        image_file = self._create_test_image_file()

        form = PhotoBulkUploadForm(data={"album": self.album1.pk}, files={"images": image_file})

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["album"], self.album1)

    @patch("photos.tasks.process_photo_async")
    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_single_image_async(self, mock_find_duplicates, mock_task):
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

        self.assertIn("created", result)
        self.assertIn("skipped", result)
        self.assertIn("errors", result)

        self.assertEqual(len(result["created"]), 1)
        self.assertEqual(len(result["skipped"]), 0)
        self.assertEqual(len(result["errors"]), 0)

        photo = result["created"][0]
        self.assertIsInstance(photo, Photo)
        self.assertEqual(photo.file_hash, "hash123")
        self.assertEqual(photo.perceptual_hash, "phash456")
        self.assertEqual(photo.processing_status, "pending")

        mock_task.delay.assert_called_once_with(photo.pk)

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_single_image_sync(self, mock_find_duplicates):
        mock_find_duplicates.return_value = {
            "exact_duplicates": [],
            "similar_images": [],
            "file_hash": "hash123",
            "perceptual_hash": "phash456",
        }

        image_file = self._create_test_image_file()
        form = PhotoBulkUploadForm(files={"images": image_file})

        self.assertTrue(form.is_valid())
        result = form.save(process_async=False)

        self.assertEqual(len(result["created"]), 1)

        photo = result["created"][0]
        self.assertIsInstance(photo, Photo)
        self.assertEqual(photo.file_hash, "hash123")
        self.assertEqual(photo.perceptual_hash, "phash456")
        self.assertEqual(photo.processing_status, "pending")

    @patch("photos.tasks.process_photo_async")
    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_multiple_images_async(self, mock_find_duplicates, mock_task):
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

        self.assertEqual(len(result["created"]), 2)
        self.assertEqual(len(result["skipped"]), 0)
        self.assertEqual(len(result["errors"]), 0)

        self.assertEqual(mock_task.delay.call_count, 2)

    @patch("photos.tasks.process_photo_async")
    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_with_album_assignment(self, mock_find_duplicates, mock_task):
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

        photo = result["created"][0]
        self.assertIn(self.album1, photo.albums.all())
        self.assertEqual(self.album1.photos.count(), 1)

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_skip_exact_duplicate(self, mock_find_duplicates):
        existing_photo = PhotoFactory.create_photo(file_hash="existing_hash")

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

        self.assertEqual(len(result["created"]), 0)
        self.assertEqual(len(result["skipped"]), 1)
        self.assertEqual(len(result["errors"]), 0)

        filename, reason = result["skipped"][0]
        self.assertEqual(filename, "test.jpg")
        self.assertIn("Exact duplicate", reason)
        self.assertIn(str(existing_photo), reason)

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_raise_on_duplicate(self, mock_find_duplicates):
        existing_photo = PhotoFactory.create_photo(file_hash="existing_hash")

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
        similar_photo = PhotoFactory.create_photo(perceptual_hash="similar_hash")

        mock_find_duplicates.return_value = {
            "exact_duplicates": [],
            "similar_images": [(similar_photo, 3)],  # distance of 3
            "file_hash": "new_hash",
            "perceptual_hash": "new_phash",
        }

        image_file = self._create_test_image_file()
        form = PhotoBulkUploadForm(files={"images": image_file})

        self.assertTrue(form.is_valid())
        result = form.save(process_async=False)

        self.assertEqual(len(result["created"]), 1)
        self.assertEqual(len(result["skipped"]), 0)
        self.assertEqual(len(result["errors"]), 0)

    @patch("photos.models.Photo.save")
    def test_save_handles_exceptions(self, mock_save):
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

            result = form.save(process_async=False)

        # Should have error
        self.assertEqual(len(result["created"]), 0)
        self.assertEqual(len(result["errors"]), 1)

        filename, error = result["errors"][0]
        self.assertEqual(filename, "test.jpg")
        self.assertIn("Database error", error)

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_mixed_results(self, mock_find_duplicates):
        existing = PhotoFactory.create_photo(file_hash="existing_hash")

        def find_duplicates_side_effect(image_file, existing_photos, **kwargs):
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

        image1 = self._create_test_image_file("success.jpg")
        image2 = self._create_test_image_file("duplicate.jpg")
        image3 = self._create_test_image_file("error.jpg")

        form = PhotoBulkUploadForm(files={"images": [image1, image2, image3]})

        self.assertTrue(form.is_valid())
        result = form.save(process_async=False)

        self.assertEqual(len(result["created"]), 1)  # Only success.jpg
        self.assertEqual(len(result["skipped"]), 1)  # duplicate.jpg
        self.assertEqual(len(result["errors"]), 1)  # error.jpg

    def test_form_invalid_no_images(self):
        form = PhotoBulkUploadForm(data={}, files={})
        self.assertFalse(form.is_valid())
        self.assertIn("images", form.errors)

    def test_form_help_text(self):
        form = PhotoBulkUploadForm()

        self.assertEqual(form.fields["images"].help_text, "You can select multiple images at once")
        self.assertEqual(
            form.fields["album"].help_text,
            "Optional: Add all uploaded photos to this album",
        )

    @patch("photos.tasks.process_photo_async")
    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_preserves_hashes_async(self, mock_find_duplicates, mock_task):
        mock_find_duplicates.return_value = {
            "exact_duplicates": [],
            "similar_images": [],
            "file_hash": "computed_file_hash",
            "perceptual_hash": "computed_perceptual_hash",
        }

        image_file = self._create_test_image_file()
        form = PhotoBulkUploadForm(files={"images": image_file})

        self.assertTrue(form.is_valid())
        result = form.save()

        photo = result["created"][0]
        self.assertEqual(photo.file_hash, "computed_file_hash")
        self.assertEqual(photo.perceptual_hash, "computed_perceptual_hash")
        self.assertEqual(photo.processing_status, "pending")

    @patch("photos.forms.DuplicateDetector.find_duplicates")
    def test_save_preserves_hashes_sync(self, mock_find_duplicates):
        mock_find_duplicates.return_value = {
            "exact_duplicates": [],
            "similar_images": [],
            "file_hash": "computed_file_hash",
            "perceptual_hash": "computed_perceptual_hash",
        }

        image_file = self._create_test_image_file()
        form = PhotoBulkUploadForm(files={"images": image_file})

        self.assertTrue(form.is_valid())

        with patch.object(Photo, "save") as mock_save:
            result = form.save(process_async=False)

            mock_save.assert_called_once_with(skip_duplicate_check=True)

        photo = result["created"][0]
        self.assertEqual(photo.file_hash, "computed_file_hash")
        self.assertEqual(photo.perceptual_hash, "computed_perceptual_hash")
