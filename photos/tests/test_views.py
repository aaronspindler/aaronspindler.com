"""
Tests for photo views.

Tests cover:
- album_detail (public/private albums, authentication)
- download_photo functionality
- download_album with zip file generation
- album_download_status endpoint
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.http import Http404
from django.core.files.base import ContentFile
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from io import BytesIO
from PIL import Image
import gc

from photos.models import Photo, PhotoAlbum
from tests.factories import UserFactory, PhotoFactory


User = get_user_model()


class AlbumDetailViewTestCase(TestCase):
    """Test cases for album_detail view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create test users
        self.regular_user = UserFactory.create_user(
            username='regular',
            password='testpass123'
        )
        self.staff_user = UserFactory.create_staff_user(
            username='staff',
            password='testpass123'
        )

        # Create test albums
        self.public_album = PhotoFactory.create_photo_album(
            title="Public Album",
            slug="public-album",
            description="A public album",
            is_private=False
        )

        self.private_album = PhotoFactory.create_photo_album(
            title="Private Album",
            slug="private-album",
            description="A private album",
            is_private=True
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
        img = Image.new('RGB', (10, 10), color=(hash(title) % 256, (hash(title) * 2) % 256, (hash(title) * 3) % 256))
        img_io = BytesIO()
        img.save(img_io, format='JPEG', quality=50)
        img_io.seek(0)

        from django.core.files.uploadedfile import SimpleUploadedFile
        test_image = SimpleUploadedFile(
            name=f'{title.lower().replace(" ", "_")}.jpg',
            content=img_io.getvalue(),
            content_type='image/jpeg'
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
        response = self.client.get(
            reverse('photos:album_detail', kwargs={'slug': 'public-album'})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Album")
        self.assertEqual(response.context['album'], self.public_album)
        self.assertEqual(len(response.context['photos']), 2)
    
    def test_public_album_authenticated_access(self):
        """Test authenticated users can access public albums."""
        self.client.login(username='regular', password='testpass123')
        
        response = self.client.get(
            reverse('photos:album_detail', kwargs={'slug': 'public-album'})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Album")
    
    def test_private_album_anonymous_denied(self):
        """Test anonymous users cannot access private albums."""
        response = self.client.get(
            reverse('photos:album_detail', kwargs={'slug': 'private-album'})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_private_album_regular_user_denied(self):
        """Test regular authenticated users cannot access private albums."""
        self.client.login(username='regular', password='testpass123')
        
        response = self.client.get(
            reverse('photos:album_detail', kwargs={'slug': 'private-album'})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_private_album_staff_access(self):
        """Test staff users can access private albums."""
        self.client.login(username='staff', password='testpass123')
        
        response = self.client.get(
            reverse('photos:album_detail', kwargs={'slug': 'private-album'})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Private Album")
        self.assertEqual(response.context['album'], self.private_album)
    
    def test_nonexistent_album(self):
        """Test accessing non-existent album returns 404."""
        response = self.client.get(
            reverse('photos:album_detail', kwargs={'slug': 'does-not-exist'})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_photo_ordering_by_date_taken(self):
        """Test photos are ordered by date_taken and created_at."""
        from datetime import datetime, timedelta
        
        # Update photos with different dates
        self.photo1.date_taken = datetime.now() - timedelta(days=2)
        self.photo1.save()
        self.photo2.date_taken = datetime.now() - timedelta(days=1)
        self.photo2.save()
        
        response = self.client.get(
            reverse('photos:album_detail', kwargs={'slug': 'public-album'})
        )
        
        photos = response.context['photos']
        # Photos should be ordered newest first
        self.assertEqual(photos[0], self.photo2)
        self.assertEqual(photos[1], self.photo1)
    
    def test_download_permissions_context(self):
        """Test download permissions are passed to template."""
        self.public_album.allow_downloads = True
        self.public_album.save()
        
        response = self.client.get(
            reverse('photos:album_detail', kwargs={'slug': 'public-album'})
        )
        
        self.assertTrue(response.context['allow_downloads'])
        
        # Disable downloads
        self.public_album.allow_downloads = False
        self.public_album.save()
        
        response = self.client.get(
            reverse('photos:album_detail', kwargs={'slug': 'public-album'})
        )
        
        self.assertFalse(response.context['allow_downloads'])


class DownloadPhotoViewTestCase(TestCase):
    """Test cases for download_photo view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create staff user
        self.staff_user = UserFactory.create_staff_user(
            username='staff',
            password='testpass123'
        )

        # Create album and photo
        self.album = PhotoFactory.create_photo_album(
            title="Test Album",
            slug="test-album",
            is_private=False,
            allow_downloads=True
        )
        
        self.photo = self._create_test_photo("Test Photo")
        self.album.photos.add(self.photo)
    
    def _create_test_photo(self, title):
        """Helper to create a test photo."""
        return PhotoFactory.create_photo(
            title=title,
            original_filename=f"{title}.jpg"
        )
    
    @patch('requests.get')
    def test_download_photo_success(self, mock_get):
        """Test successful photo download."""
        # Mock S3 response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'image_content'
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_get.return_value = mock_response
        
        # Mock image URL
        with patch.object(self.photo, 'get_image_url', return_value='http://s3.example.com/photo.jpg'):
            response = self.client.get(
                reverse('photos:download_photo', 
                       kwargs={'slug': 'test-album', 'photo_id': self.photo.id})
            )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('.jpg', response['Content-Disposition'])  # Should contain some jpg filename
    
    def test_download_photo_album_not_found(self):
        """Test download from non-existent album."""
        response = self.client.get(
            reverse('photos:download_photo',
                   kwargs={'slug': 'nonexistent', 'photo_id': self.photo.id})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_download_photo_not_in_album(self):
        """Test downloading photo not in the specified album."""
        other_photo = self._create_test_photo("Other Photo")
        
        response = self.client.get(
            reverse('photos:download_photo',
                   kwargs={'slug': 'test-album', 'photo_id': other_photo.id})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_download_disabled(self):
        """Test download when album downloads are disabled."""
        self.album.allow_downloads = False
        self.album.save()
        
        response = self.client.get(
            reverse('photos:download_photo',
                   kwargs={'slug': 'test-album', 'photo_id': self.photo.id})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_download_private_album_anonymous(self):
        """Test anonymous user cannot download from private album."""
        self.album.is_private = True
        self.album.save()
        
        response = self.client.get(
            reverse('photos:download_photo',
                   kwargs={'slug': 'test-album', 'photo_id': self.photo.id})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_download_private_album_staff(self):
        """Test staff can download from private album."""
        self.album.is_private = True
        self.album.save()
        self.client.login(username='staff', password='testpass123')
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'image_content'
            mock_response.headers = {'content-type': 'image/jpeg'}
            mock_get.return_value = mock_response
            
            with patch.object(self.photo, 'get_image_url', return_value='http://s3.example.com/photo.jpg'):
                response = self.client.get(
                    reverse('photos:download_photo',
                           kwargs={'slug': 'test-album', 'photo_id': self.photo.id})
                )
        
        self.assertEqual(response.status_code, 200)
    
    @patch('requests.get')
    def test_download_photo_s3_error(self, mock_get):
        """Test handling S3 download errors."""
        # Mock S3 error response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response
        
        with patch.object(self.photo, 'get_image_url', return_value='http://s3.example.com/photo.jpg'):
            response = self.client.get(
                reverse('photos:download_photo',
                       kwargs={'slug': 'test-album', 'photo_id': self.photo.id})
            )
        
        self.assertEqual(response.status_code, 404)
    
    @patch('requests.get')
    def test_download_photo_network_error(self, mock_get):
        """Test handling network errors during download."""
        import requests
        mock_get.side_effect = requests.RequestException("Network error")
        
        with patch.object(self.photo, 'get_image_url', return_value='http://s3.example.com/photo.jpg'):
            response = self.client.get(
                reverse('photos:download_photo',
                       kwargs={'slug': 'test-album', 'photo_id': self.photo.id})
            )
        
        self.assertEqual(response.status_code, 404)


class DownloadAlbumViewTestCase(TestCase):
    """Test cases for download_album view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create users
        self.regular_user = UserFactory.create_user(
            username='regular',
            password='testpass123'
        )
        self.staff_user = UserFactory.create_staff_user(
            username='staff',
            password='testpass123'
        )

        # Create album
        self.album = PhotoFactory.create_photo_album(
            title="Download Test Album",
            slug="download-test",
            is_private=False,
            allow_downloads=True
        )
    
    def test_download_album_optimized_redirect(self):
        """Test downloading optimized zip redirects to URL."""
        # Create actual zip file to pass the existence check
        from django.core.files.base import ContentFile
        self.album.zip_file_optimized.save('test.zip', ContentFile(b'test'), save=True)
        
        # Mock the URL property using PropertyMock
        with patch.object(type(self.album.zip_file_optimized), 'url', new_callable=PropertyMock(return_value='http://s3.example.com/album_optimized.zip')):
            response = self.client.get(
                reverse('photos:download_album',
                       kwargs={'slug': 'download-test'})
            )
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'http://s3.example.com/album_optimized.zip')
    
    def test_download_album_original_quality(self):
        """Test downloading original quality zip."""
        # Create actual zip file to pass the existence check
        from django.core.files.base import ContentFile
        self.album.zip_file.save('test.zip', ContentFile(b'test'), save=True)
        
        # Mock the URL property using PropertyMock
        with patch.object(type(self.album.zip_file), 'url', new_callable=PropertyMock(return_value='http://s3.example.com/album_original.zip')):
            response = self.client.get(
                reverse('photos:download_album_quality',
                       kwargs={'slug': 'download-test', 'quality': 'original'})
            )
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'http://s3.example.com/album_original.zip')
    
    def test_download_album_invalid_quality(self):
        """Test invalid quality defaults to optimized."""
        # Create actual zip file to pass the existence check
        from django.core.files.base import ContentFile
        self.album.zip_file_optimized.save('test.zip', ContentFile(b'test'), save=True)
        
        # Mock the URL property using PropertyMock
        with patch.object(type(self.album.zip_file_optimized), 'url', new_callable=PropertyMock(return_value='http://s3.example.com/album_optimized.zip')):
            response = self.client.get(
                reverse('photos:download_album_quality',
                       kwargs={'slug': 'download-test', 'quality': 'invalid'})
            )
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'http://s3.example.com/album_optimized.zip')
    
    @patch('photos.tasks.generate_album_zip.delay')
    def test_download_album_no_zip_triggers_generation(self, mock_task):
        """Test missing zip file triggers generation."""
        self.album.zip_file = None
        self.album.zip_file_optimized = None
        
        response = self.client.get(
            reverse('photos:download_album',
                   kwargs={'slug': 'download-test'})
        )
        
        self.assertEqual(response.status_code, 404)
        mock_task.assert_called_once_with(self.album.pk)
        # The Http404 message is preserved in test responses
        # but rendered through the 404.html template
    
    def test_download_album_disabled(self):
        """Test download when downloads are disabled."""
        self.album.allow_downloads = False
        self.album.save()
        
        response = self.client.get(
            reverse('photos:download_album',
                   kwargs={'slug': 'download-test'})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_download_private_album_anonymous(self):
        """Test anonymous user cannot download private album."""
        self.album.is_private = True
        self.album.save()
        
        response = self.client.get(
            reverse('photos:download_album',
                   kwargs={'slug': 'download-test'})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_download_private_album_staff(self):
        """Test staff can download private album."""
        self.album.is_private = True
        self.album.save()
        self.client.login(username='staff', password='testpass123')
        
        # Create actual zip file to pass the existence check
        from django.core.files.base import ContentFile
        self.album.zip_file_optimized.save('test.zip', ContentFile(b'test'), save=True)
        
        # Mock the URL property by patching the storage backend
        with patch('django.core.files.storage.default_storage.url', return_value='http://s3.example.com/album.zip'):
            response = self.client.get(
                reverse('photos:download_album',
                       kwargs={'slug': 'download-test'})
            )
        
        self.assertEqual(response.status_code, 302)
    
    def test_download_album_url_error(self):
        """Test handling errors getting download URL."""
        mock_zip = Mock()
        mock_zip.url = PropertyMock(side_effect=Exception("S3 error"))
        self.album.zip_file_optimized = mock_zip
        
        response = self.client.get(
            reverse('photos:download_album',
                   kwargs={'slug': 'download-test'})
        )
        
        self.assertEqual(response.status_code, 404)


class AlbumDownloadStatusViewTestCase(TestCase):
    """Test cases for album_download_status view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create users
        self.staff_user = UserFactory.create_staff_user(
            username='staff',
            password='testpass123'
        )

        # Create album with photos
        self.album = PhotoFactory.create_photo_album(
            title="Status Test Album",
            slug="status-test",
            is_private=False,
            allow_downloads=True
        )
        
        # Add photos
        self.photo1 = self._create_test_photo("Photo 1")
        self.photo2 = self._create_test_photo("Photo 2")
        self.album.photos.add(self.photo1, self.photo2)
    
    def _create_test_photo(self, title):
        """Helper to create a test photo with unique image."""
        # Create unique image to avoid duplicate detection
        img = Image.new('RGB', (10, 10), color=(hash(title) % 256, (hash(title) * 2) % 256, (hash(title) * 3) % 256))
        img_io = BytesIO()
        img.save(img_io, format='JPEG', quality=50)
        img_io.seek(0)

        from django.core.files.uploadedfile import SimpleUploadedFile
        test_image = SimpleUploadedFile(
            name=f'{title.lower().replace(" ", "_")}.jpg',
            content=img_io.getvalue(),
            content_type='image/jpeg'
        )

        photo = Photo(title=title, image=test_image)
        photo.save(skip_duplicate_check=True)
        return photo
    
    def test_status_with_both_zips(self):
        """Test status when both zip files exist."""
        # Create both zip files
        from django.core.files.base import ContentFile
        self.album.zip_file.save('test.zip', ContentFile(b'test'), save=False)
        self.album.zip_file_optimized.save('test_opt.zip', ContentFile(b'test'), save=False)
        self.album.save()
        
        # Mock the album retrieval to return an album with mocked file sizes
        def mock_get_object_or_404(model, **kwargs):
            if model == PhotoAlbum and kwargs.get('slug') == 'status-test':
                mock_album = MagicMock()
                mock_album.title = "Status Test Album"
                mock_album.photos.count.return_value = 2
                mock_album.allow_downloads = True
                
                # Mock zip files with specific sizes
                mock_album.zip_file.size = 1024000
                mock_album.zip_file.__bool__ = lambda self: True
                mock_album.zip_file_optimized.size = 512000
                mock_album.zip_file_optimized.__bool__ = lambda self: True
                
                return mock_album
            return self.album
        
        with patch('photos.views.get_object_or_404', side_effect=mock_get_object_or_404):
            response = self.client.get(
                reverse('photos:album_download_status',
                       kwargs={'slug': 'status-test'})
            )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['album_title'], "Status Test Album")
        self.assertEqual(data['photo_count'], 2)
        self.assertTrue(data['downloads_allowed'])
        self.assertTrue(data['original']['ready'])
        self.assertEqual(data['original']['size'], 1024000)
        self.assertTrue(data['optimized']['ready'])
        self.assertEqual(data['optimized']['size'], 512000)
    
    @patch('photos.tasks.generate_album_zip.delay')
    def test_status_no_zips_triggers_generation(self, mock_task):
        """Test status when no zip files exist triggers generation."""
        self.album.zip_file = None
        self.album.zip_file_optimized = None
        
        response = self.client.get(
            reverse('photos:album_download_status',
                   kwargs={'slug': 'status-test'})
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertFalse(data['original']['ready'])
        self.assertFalse(data['optimized']['ready'])
        self.assertTrue(data.get('generation_triggered', False))
        mock_task.assert_called_once_with(self.album.pk)
    
    def test_status_downloads_disabled(self):
        """Test status when downloads are disabled."""
        self.album.allow_downloads = False
        self.album.save()
        
        response = self.client.get(
            reverse('photos:album_download_status',
                   kwargs={'slug': 'status-test'})
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['error'], 'Downloads not allowed')
    
    def test_status_private_album_anonymous(self):
        """Test status for private album as anonymous user."""
        self.album.is_private = True
        self.album.save()
        
        response = self.client.get(
            reverse('photos:album_download_status',
                   kwargs={'slug': 'status-test'})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_status_private_album_staff(self):
        """Test status for private album as staff user."""
        self.album.is_private = True
        self.album.save()
        self.client.login(username='staff', password='testpass123')
        
        response = self.client.get(
            reverse('photos:album_download_status',
                   kwargs={'slug': 'status-test'})
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['album_title'], "Status Test Album")
    
    def test_status_nonexistent_album(self):
        """Test status for non-existent album."""
        response = self.client.get(
            reverse('photos:album_download_status',
                   kwargs={'slug': 'does-not-exist'})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_status_partial_zips(self):
        """Test status when only one zip file exists."""
        # Create only original zip file
        from django.core.files.base import ContentFile
        self.album.zip_file.save('test.zip', ContentFile(b'test'), save=True)
        
        # Mock the file size property
        with patch('os.path.getsize', return_value=1024000):
            response = self.client.get(
                reverse('photos:album_download_status',
                       kwargs={'slug': 'status-test'})
            )
        
        data = response.json()
        self.assertTrue(data['original']['ready'])
        self.assertFalse(data['optimized']['ready'])
        self.assertIsNone(data['optimized']['size'])

