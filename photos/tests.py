"""
Comprehensive test suite for the photos application.
"""
import os
import tempfile
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
from django.test import TestCase, RequestFactory, override_settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models.signals import post_save, pre_delete
from django.conf import settings

from .models import Album, Photo
from .views import AlbumListView, AlbumDetailView
from .utils import (
    generate_thumbnail,
    validate_image,
    get_thumbnail_filename,
    cleanup_s3_file,
    process_uploaded_image
)
from .signals import create_thumbnail, delete_photo_files, update_album_cover
from .storage import MediaStorage

User = get_user_model()


class AlbumModelTests(TestCase):
    """Test cases for the Album model."""
    
    def setUp(self):
        """Set up test data."""
        self.album = Album.objects.create(
            title="Test Album",
            description="Test Description",
            is_published=True,
            order=1
        )
    
    def test_album_creation(self):
        """Test that an album can be created with basic fields."""
        self.assertEqual(self.album.title, "Test Album")
        self.assertEqual(self.album.description, "Test Description")
        self.assertTrue(self.album.is_published)
        self.assertEqual(self.album.order, 1)
        self.assertIsNotNone(self.album.created_at)
        self.assertIsNotNone(self.album.updated_at)
    
    def test_album_str_representation(self):
        """Test the string representation of an album."""
        self.assertEqual(str(self.album), "Test Album")
    
    def test_album_photo_count(self):
        """Test the photo_count method."""
        self.assertEqual(self.album.photo_count(), 0)
        
        # Create a photo for the album
        Photo.objects.create(
            album=self.album,
            title="Test Photo",
            original_image=SimpleUploadedFile("test.jpg", b"content")
        )
        
        self.assertEqual(self.album.photo_count(), 1)
    
    def test_album_default_ordering(self):
        """Test that albums are ordered by created_at descending."""
        album2 = Album.objects.create(title="Second Album")
        albums = Album.objects.all()
        self.assertEqual(albums[0], album2)  # Most recent first
        self.assertEqual(albums[1], self.album)
    
    def test_album_verbose_names(self):
        """Test verbose names for the Album model."""
        self.assertEqual(Album._meta.verbose_name, "Album")
        self.assertEqual(Album._meta.verbose_name_plural, "Albums")


class PhotoModelTests(TestCase):
    """Test cases for the Photo model."""
    
    def setUp(self):
        """Set up test data."""
        self.album = Album.objects.create(
            title="Test Album",
            is_published=True
        )
        
        # Create a simple test image
        self.test_image = SimpleUploadedFile(
            name='test.jpg',
            content=b'fake_image_content',
            content_type='image/jpeg'
        )
    
    def test_photo_creation(self):
        """Test that a photo can be created with basic fields."""
        photo = Photo.objects.create(
            album=self.album,
            title="Test Photo",
            caption="Test Caption",
            original_image=self.test_image,
            order=1
        )
        
        self.assertEqual(photo.album, self.album)
        self.assertEqual(photo.title, "Test Photo")
        self.assertEqual(photo.caption, "Test Caption")
        self.assertEqual(photo.order, 1)
        self.assertIsNotNone(photo.created_at)
        self.assertTrue(photo.original_image.name.endswith('.jpg'))
    
    def test_photo_str_representation(self):
        """Test the string representation of a photo."""
        photo_with_title = Photo.objects.create(
            album=self.album,
            title="Named Photo",
            original_image=SimpleUploadedFile("test1.jpg", b"content")
        )
        photo_without_title = Photo.objects.create(
            album=self.album,
            original_image=SimpleUploadedFile("test2.jpg", b"content")
        )
        
        self.assertEqual(str(photo_with_title), "Named Photo - Test Album")
        self.assertEqual(str(photo_without_title), "Photo in Test Album")
    
    def test_photo_default_ordering(self):
        """Test that photos are ordered by order field, then created_at descending."""
        photo1 = Photo.objects.create(
            album=self.album,
            order=2,
            original_image=SimpleUploadedFile("test1.jpg", b"content")
        )
        photo2 = Photo.objects.create(
            album=self.album,
            order=1,
            original_image=SimpleUploadedFile("test2.jpg", b"content")
        )
        photo3 = Photo.objects.create(
            album=self.album,
            order=1,
            original_image=SimpleUploadedFile("test3.jpg", b"content")
        )
        
        photos = Photo.objects.all()
        self.assertEqual(photos[0], photo2)  # order=1, created earlier
        self.assertEqual(photos[1], photo3)  # order=1, created later
        self.assertEqual(photos[2], photo1)  # order=2
    
    def test_photo_verbose_names(self):
        """Test verbose names for the Photo model."""
        self.assertEqual(Photo._meta.verbose_name, "Photo")
        self.assertEqual(Photo._meta.verbose_name_plural, "Photos")
    
    @patch('photos.models.super')
    def test_photo_save_method(self, mock_super):
        """Test the custom save method for photos."""
        mock_super_instance = MagicMock()
        mock_super.return_value = mock_super_instance
        
        photo = Photo(
            album=self.album,
            title="Test Photo",
            original_image=self.test_image
        )
        photo.save()
        
        # Verify super().save() was called
        self.assertTrue(mock_super_instance.save.called)


class AlbumListViewTests(TestCase):
    """Test cases for AlbumListView."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.published_album = Album.objects.create(
            title="Published Album",
            is_published=True,
            order=1
        )
        self.unpublished_album = Album.objects.create(
            title="Unpublished Album",
            is_published=False,
            order=2
        )
        self.view = AlbumListView.as_view()
    
    def test_list_view_filters_published_albums(self):
        """Test that the list view only shows published albums."""
        request = self.factory.get('/albums/')
        response = self.view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.published_album, response.context_data['albums'])
        self.assertNotIn(self.unpublished_album, response.context_data['albums'])
    
    def test_list_view_ordering(self):
        """Test that albums are ordered correctly."""
        album2 = Album.objects.create(
            title="Second Album",
            is_published=True,
            order=0
        )
        
        request = self.factory.get('/albums/')
        response = self.view(request)
        
        albums = list(response.context_data['albums'])
        self.assertEqual(albums[0], album2)  # order=0
        self.assertEqual(albums[1], self.published_album)  # order=1
    
    def test_list_view_pagination(self):
        """Test pagination in the list view."""
        # Create 13 published albums (already have 1)
        for i in range(12):
            Album.objects.create(
                title=f"Album {i}",
                is_published=True
            )
        
        request = self.factory.get('/albums/')
        response = self.view(request)
        
        # Should have 12 albums on first page (paginate_by=12)
        self.assertEqual(len(response.context_data['albums']), 12)
        self.assertTrue(response.context_data['is_paginated'])
    
    def test_list_view_template_and_context(self):
        """Test correct template and context variable names."""
        request = self.factory.get('/albums/')
        response = self.view(request)
        
        self.assertEqual(response.template_name[0], 'photos/album_list.html')
        self.assertIn('albums', response.context_data)


class AlbumDetailViewTests(TestCase):
    """Test cases for AlbumDetailView."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.album = Album.objects.create(
            title="Test Album",
            is_published=True
        )
        self.unpublished_album = Album.objects.create(
            title="Unpublished Album",
            is_published=False
        )
        
        # Create photos for the album
        for i in range(3):
            Photo.objects.create(
                album=self.album,
                title=f"Photo {i}",
                order=i,
                original_image=SimpleUploadedFile(f"test{i}.jpg", b"content")
            )
    
    def test_detail_view_shows_published_album(self):
        """Test that the detail view shows published albums."""
        view = AlbumDetailView.as_view()
        request = self.factory.get(f'/albums/{self.album.pk}/')
        response = view(request, pk=self.album.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['album'], self.album)
    
    def test_detail_view_filters_unpublished_albums(self):
        """Test that unpublished albums raise 404."""
        view = AlbumDetailView.as_view()
        request = self.factory.get(f'/albums/{self.unpublished_album.pk}/')
        
        with self.assertRaises(Album.DoesNotExist):
            view(request, pk=self.unpublished_album.pk)
    
    def test_detail_view_includes_photos_in_context(self):
        """Test that photos are included in the context."""
        view = AlbumDetailView.as_view()
        request = self.factory.get(f'/albums/{self.album.pk}/')
        response = view(request, pk=self.album.pk)
        
        self.assertIn('photos', response.context_data)
        self.assertEqual(len(response.context_data['photos']), 3)
    
    def test_detail_view_photo_ordering(self):
        """Test that photos are ordered correctly."""
        view = AlbumDetailView.as_view()
        request = self.factory.get(f'/albums/{self.album.pk}/')
        response = view(request, pk=self.album.pk)
        
        photos = list(response.context_data['photos'])
        for i, photo in enumerate(photos):
            self.assertEqual(photo.title, f"Photo {i}")
    
    def test_detail_view_template(self):
        """Test correct template is used."""
        view = AlbumDetailView.as_view()
        request = self.factory.get(f'/albums/{self.album.pk}/')
        response = view(request, pk=self.album.pk)
        
        self.assertEqual(response.template_name[0], 'photos/album_detail.html')


class UtilityFunctionTests(TestCase):
    """Test cases for utility functions."""
    
    def create_test_image(self, format='JPEG', size=(100, 100), color='red'):
        """Helper method to create a test image."""
        image = Image.new('RGB', size, color)
        io = BytesIO()
        image.save(io, format=format)
        io.seek(0)
        return io
    
    def test_generate_thumbnail_success(self):
        """Test successful thumbnail generation."""
        test_image = self.create_test_image()
        
        thumbnail = generate_thumbnail(test_image, size=(50, 50))
        
        self.assertIsNotNone(thumbnail)
        self.assertIsInstance(thumbnail, ContentFile)
        
        # Verify thumbnail was created
        thumb_image = Image.open(thumbnail)
        self.assertLessEqual(thumb_image.width, 50)
        self.assertLessEqual(thumb_image.height, 50)
    
    def test_generate_thumbnail_with_transparent_image(self):
        """Test thumbnail generation with transparent images."""
        # Create RGBA image with transparency
        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        io = BytesIO()
        image.save(io, format='PNG')
        io.seek(0)
        
        thumbnail = generate_thumbnail(io)
        
        self.assertIsNotNone(thumbnail)
        # Verify it was converted to JPEG (RGB)
        thumb_image = Image.open(thumbnail)
        self.assertEqual(thumb_image.mode, 'RGB')
    
    @patch('photos.utils.logger')
    def test_generate_thumbnail_failure(self, mock_logger):
        """Test thumbnail generation failure handling."""
        invalid_image = BytesIO(b"invalid image data")
        
        result = generate_thumbnail(invalid_image)
        
        self.assertIsNone(result)
        mock_logger.error.assert_called()
    
    def test_validate_image_valid(self):
        """Test validation of a valid image."""
        test_image = SimpleUploadedFile(
            "test.jpg",
            self.create_test_image().getvalue(),
            content_type="image/jpeg"
        )
        test_image.size = 1024 * 1024  # 1MB
        
        is_valid, error = validate_image(test_image)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_image_too_large(self):
        """Test validation rejects images that are too large."""
        test_image = SimpleUploadedFile("test.jpg", b"content")
        test_image.size = 11 * 1024 * 1024  # 11MB
        
        is_valid, error = validate_image(test_image)
        
        self.assertFalse(is_valid)
        self.assertIn("10MB", error)
    
    def test_validate_image_invalid_extension(self):
        """Test validation rejects invalid file extensions."""
        test_image = SimpleUploadedFile("test.bmp", b"content")
        test_image.size = 1024
        
        is_valid, error = validate_image(test_image)
        
        self.assertFalse(is_valid)
        self.assertIn("Invalid file extension", error)
    
    def test_validate_image_invalid_content(self):
        """Test validation rejects invalid image content."""
        test_image = SimpleUploadedFile("test.jpg", b"not an image")
        test_image.size = 1024
        
        is_valid, error = validate_image(test_image)
        
        self.assertFalse(is_valid)
        self.assertIn("Invalid image file", error)
    
    def test_get_thumbnail_filename(self):
        """Test thumbnail filename generation."""
        self.assertEqual(
            get_thumbnail_filename("photo.jpg"),
            "photo_thumb.jpg"
        )
        self.assertEqual(
            get_thumbnail_filename("image.png"),
            "image_thumb.jpg"
        )
        self.assertEqual(
            get_thumbnail_filename("path/to/file.jpeg"),
            "path/to/file_thumb.jpg"
        )
    
    @patch('photos.utils.logger')
    def test_cleanup_s3_file_success(self, mock_logger):
        """Test successful S3 file cleanup."""
        mock_file = Mock()
        mock_file.delete.return_value = None
        
        result = cleanup_s3_file(mock_file)
        
        self.assertTrue(result)
        mock_file.delete.assert_called_once_with(save=False)
    
    @patch('photos.utils.logger')
    def test_cleanup_s3_file_failure(self, mock_logger):
        """Test S3 file cleanup failure handling."""
        mock_file = Mock()
        mock_file.name = "test.jpg"
        mock_file.delete.side_effect = Exception("S3 Error")
        
        result = cleanup_s3_file(mock_file)
        
        self.assertFalse(result)
        mock_logger.error.assert_called()
    
    def test_cleanup_s3_file_empty(self):
        """Test cleanup with empty file field."""
        result = cleanup_s3_file(None)
        self.assertTrue(result)
    
    def test_process_uploaded_image_valid(self):
        """Test processing a valid uploaded image."""
        test_image = SimpleUploadedFile(
            "test.jpg",
            self.create_test_image(size=(100, 100)).getvalue(),
            content_type="image/jpeg"
        )
        test_image.size = 1024 * 1024  # 1MB
        
        processed, error = process_uploaded_image(test_image)
        
        self.assertIsNotNone(processed)
        self.assertIsNone(error)
    
    def test_process_uploaded_image_large_dimensions(self):
        """Test processing an image with large dimensions."""
        test_image = SimpleUploadedFile(
            "test.jpg",
            self.create_test_image(size=(5000, 5000)).getvalue(),
            content_type="image/jpeg"
        )
        test_image.size = 1024 * 1024  # 1MB
        
        processed, error = process_uploaded_image(test_image)
        
        self.assertIsNotNone(processed)
        self.assertIsNone(error)
        
        # Verify image was resized
        processed_img = Image.open(processed)
        self.assertLessEqual(processed_img.width, 4000)
        self.assertLessEqual(processed_img.height, 4000)
    
    def test_process_uploaded_image_invalid(self):
        """Test processing an invalid image."""
        test_image = SimpleUploadedFile("test.txt", b"not an image")
        test_image.size = 1024
        
        processed, error = process_uploaded_image(test_image)
        
        self.assertIsNone(processed)
        self.assertIsNotNone(error)
    
    @patch('photos.utils.logger')
    def test_process_uploaded_image_processing_error(self, mock_logger):
        """Test handling of processing errors."""
        test_image = SimpleUploadedFile("test.jpg", b"content")
        test_image.size = 1024
        
        with patch('photos.utils.validate_image', return_value=(True, None)):
            with patch('photos.utils.Image.open', side_effect=Exception("Processing error")):
                processed, error = process_uploaded_image(test_image)
        
        self.assertIsNone(processed)
        self.assertIn("Failed to process image", error)
        mock_logger.error.assert_called()


class SignalTests(TestCase):
    """Test cases for signal handlers."""
    
    def setUp(self):
        """Set up test data."""
        self.album = Album.objects.create(
            title="Test Album",
            is_published=True
        )
    
    @patch('photos.signals.generate_thumbnail')
    @patch('photos.signals.get_thumbnail_filename')
    def test_create_thumbnail_signal(self, mock_get_filename, mock_generate):
        """Test thumbnail creation signal."""
        # Disconnect the actual signal to test in isolation
        post_save.disconnect(create_thumbnail, sender=Photo)
        
        mock_generate.return_value = ContentFile(b"thumbnail_content")
        mock_get_filename.return_value = "test_thumb.jpg"
        
        photo = Photo(
            album=self.album,
            original_image=SimpleUploadedFile("test.jpg", b"content")
        )
        
        # Manually trigger the signal
        create_thumbnail(sender=Photo, instance=photo, created=True, raw=False)
        
        mock_generate.assert_called_once()
        mock_get_filename.assert_called_once()
        
        # Reconnect the signal
        post_save.connect(create_thumbnail, sender=Photo)
    
    @patch('photos.signals.cleanup_s3_file')
    def test_delete_photo_files_signal(self, mock_cleanup):
        """Test photo deletion signal."""
        # Disconnect the actual signal to test in isolation
        pre_delete.disconnect(delete_photo_files, sender=Photo)
        
        mock_cleanup.return_value = True
        
        photo = Photo(
            pk=1,
            album=self.album,
            original_image=SimpleUploadedFile("test.jpg", b"content"),
            thumbnail=SimpleUploadedFile("thumb.jpg", b"content")
        )
        
        # Manually trigger the signal
        delete_photo_files(sender=Photo, instance=photo)
        
        # Should be called twice (original and thumbnail)
        self.assertEqual(mock_cleanup.call_count, 2)
        
        # Reconnect the signal
        pre_delete.connect(delete_photo_files, sender=Photo)
    
    def test_update_album_cover_signal(self):
        """Test album cover update signal."""
        # Disconnect other signals to isolate this test
        post_save.disconnect(create_thumbnail, sender=Photo)
        
        # Create album without cover
        album = Album.objects.create(
            title="No Cover Album",
            is_published=True
        )
        
        self.assertFalse(album.cover_image)
        
        # Create first photo
        photo = Photo(
            album=album,
            original_image=SimpleUploadedFile("test.jpg", b"content"),
            thumbnail=SimpleUploadedFile("thumb.jpg", b"content")
        )
        
        # Manually trigger the signal
        update_album_cover(sender=Photo, instance=photo, created=True)
        
        # Refresh album from database
        album.refresh_from_db()
        
        # Album should now have a cover
        self.assertTrue(album.cover_image)
        
        # Reconnect the signal
        post_save.connect(create_thumbnail, sender=Photo)
    
    @patch('photos.signals.logger')
    def test_signal_error_handling(self, mock_logger):
        """Test that signals handle errors gracefully."""
        # Test create_thumbnail error handling
        photo = Photo(
            album=self.album,
            original_image=SimpleUploadedFile("test.jpg", b"content")
        )
        
        with patch('photos.signals.generate_thumbnail', side_effect=Exception("Error")):
            # Should not raise exception
            create_thumbnail(sender=Photo, instance=photo, created=True)
            mock_logger.error.assert_called()


class MediaStorageTests(TestCase):
    """Test cases for the MediaStorage class."""
    
    @override_settings(
        AWS_STORAGE_BUCKET_NAME='test-bucket',
        AWS_S3_CUSTOM_DOMAIN='test.cloudfront.net',
        AWS_ACCESS_KEY_ID='test-key',
        AWS_SECRET_ACCESS_KEY='test-secret',
        AWS_S3_REGION_NAME='us-east-1'
    )
    def test_storage_initialization(self):
        """Test MediaStorage initialization with settings."""
        storage = MediaStorage()
        
        self.assertEqual(storage.bucket_name, 'test-bucket')
        self.assertEqual(storage.custom_domain, 'test.cloudfront.net')
        self.assertFalse(storage.file_overwrite)
        self.assertEqual(storage.default_acl, 'public-read')
        self.assertEqual(storage.access_key, 'test-key')
        self.assertEqual(storage.secret_key, 'test-secret')
        self.assertEqual(storage.region_name, 'us-east-1')
    
    @override_settings(
        AWS_S3_CUSTOM_DOMAIN='test.cloudfront.net'
    )
    def test_storage_url_generation(self):
        """Test URL generation for stored files."""
        storage = MediaStorage()
        
        url = storage.url('path/to/file.jpg')
        
        self.assertEqual(url, 'https://test.cloudfront.net/path/to/file.jpg')
    
    def test_storage_get_available_name(self):
        """Test that get_available_name works correctly."""
        storage = MediaStorage()
        
        with patch.object(storage, 'exists', return_value=False):
            name = storage.get_available_name('test.jpg')
            self.assertEqual(name, 'test.jpg')


class IntegrationTests(TestCase):
    """Integration tests for the complete photo upload flow."""
    
    @patch('photos.signals.generate_thumbnail')
    @patch('photos.utils.cleanup_s3_file')
    def test_complete_photo_lifecycle(self, mock_cleanup, mock_generate):
        """Test complete photo lifecycle from creation to deletion."""
        mock_generate.return_value = ContentFile(b"thumbnail")
        mock_cleanup.return_value = True
        
        # Create album
        album = Album.objects.create(
            title="Test Album",
            is_published=True
        )
        
        # Create photo (should trigger thumbnail generation)
        photo = Photo.objects.create(
            album=album,
            title="Test Photo",
            original_image=SimpleUploadedFile("test.jpg", b"content")
        )
        
        self.assertEqual(photo.album, album)
        
        # Delete photo (should trigger cleanup)
        photo_id = photo.id
        photo.delete()
        
        # Verify photo was deleted
        self.assertFalse(Photo.objects.filter(id=photo_id).exists())
        
        # Verify cleanup was called
        self.assertTrue(mock_cleanup.called)
    
    def test_album_with_multiple_photos(self):
        """Test album with multiple photos."""
        album = Album.objects.create(
            title="Multi-Photo Album",
            is_published=True
        )
        
        # Create multiple photos
        photos = []
        for i in range(5):
            photo = Photo.objects.create(
                album=album,
                title=f"Photo {i}",
                order=i,
                original_image=SimpleUploadedFile(f"test{i}.jpg", b"content")
            )
            photos.append(photo)
        
        # Verify photo count
        self.assertEqual(album.photo_count(), 5)
        
        # Verify ordering
        album_photos = album.photos.all()
        for i, photo in enumerate(album_photos):
            self.assertEqual(photo.order, i)


# Add test runner configuration for coverage
class TestRunner:
    """Custom test runner for coverage reporting."""
    
    @staticmethod
    def run_tests():
        """Run all tests with coverage reporting."""
        import coverage
        cov = coverage.Coverage()
        cov.start()
        
        # Run tests
        from django.test.utils import get_runner
        from django.conf import settings
        TestRunnerClass = get_runner(settings)
        test_runner = TestRunnerClass()
        failures = test_runner.run_tests(["photos"])
        
        cov.stop()
        cov.save()
        
        # Print coverage report
        print("\nCoverage Report:")
        cov.report()
        
        return failures