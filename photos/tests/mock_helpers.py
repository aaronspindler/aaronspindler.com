"""
Mock helpers for photo tests to reduce memory usage and improve test performance.

This module provides common mocks for heavy image processing operations that
aren't essential to test functionality but consume significant resources.
"""

from unittest.mock import MagicMock
from io import BytesIO
from PIL import Image


def create_tiny_test_image(size=(10, 10), color='blue', format='JPEG'):
    """Create a tiny test image to minimize memory usage."""
    img = Image.new('RGB', size, color=color)
    img_io = BytesIO()
    img.save(img_io, format=format, quality=50)
    img_io.seek(0)
    return img_io


def mock_image_optimizer_process():
    """Create a mock for ImageOptimizer.process_uploaded_image."""
    mock_optimized = MagicMock(name='optimized.jpg')
    mock_display = MagicMock(name='display.jpg')
    return (
        {'optimized': mock_optimized, 'display': mock_display},
        (0.5, 0.5)  # focal point
    )


def mock_duplicate_detector_hashes(identifier='test'):
    """Create a mock for DuplicateDetector.compute_and_store_hashes."""
    return {
        'file_hash': f'hash_{identifier}',
        'perceptual_hash': f'phash_{identifier}'
    }


def mock_exif_extractor_data(basic=True):
    """Create mock EXIF data."""
    if basic:
        return {}
    
    return {
        'camera_make': 'Canon',
        'camera_model': 'EOS R5',
        'iso': 400,
        'aperture': 'f/2.8',
        'shutter_speed': '1/250',
        'focal_length': '50mm',
        'date_taken': None,
        'full_exif': {}
    }


def mock_image_metadata(width=10, height=10, file_size=1024):
    """Create mock image metadata."""
    return {
        'width': width,
        'height': height,
        'file_size': file_size,
        'format': 'JPEG',
        'mode': 'RGB'
    }


class PhotoTestMixin:
    """Mixin to provide common photo test utilities."""
    
    @staticmethod
    def create_mock_photo_with_minimal_processing(title="Test Photo"):
        """
        Create a photo with all heavy operations mocked.
        
        This should be used in tests that don't need to test the actual
        image processing functionality.
        """
        from unittest.mock import patch
        from photos.models import Photo
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create tiny test image
        img_io = create_tiny_test_image()
        test_image = SimpleUploadedFile(
            name=f'{title.lower().replace(" ", "_")}.jpg',
            content=img_io.getvalue(),
            content_type='image/jpeg'
        )
        
        # Mock all heavy operations
        with patch('photos.models.ImageOptimizer.process_uploaded_image') as mock_process, \
             patch('photos.models.DuplicateDetector.compute_and_store_hashes') as mock_hashes, \
             patch('photos.models.ExifExtractor.extract_exif') as mock_exif, \
             patch('photos.models.ImageMetadataExtractor.extract_basic_metadata') as mock_metadata:
            
            mock_process.return_value = mock_image_optimizer_process()
            mock_hashes.return_value = mock_duplicate_detector_hashes(title)
            mock_exif.return_value = mock_exif_extractor_data()
            mock_metadata.return_value = mock_image_metadata()
            
            photo = Photo(title=title, image=test_image)
            photo.save(skip_duplicate_check=True)
            return photo
