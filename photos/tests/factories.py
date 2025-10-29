"""
Test data factories for creating consistent fake photo data across all tests.

This module provides factory functions to create test photo instances with
consistent, realistic fake data that can be reused across all test files.
"""

from datetime import datetime
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


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
