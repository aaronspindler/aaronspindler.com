from datetime import datetime
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image


class PhotoFactory:
    @staticmethod
    def create_test_image(size=(100, 100), color=(255, 0, 0), format="JPEG"):
        img = Image.new("RGB", size, color)
        img_io = BytesIO()
        img.save(img_io, format=format)
        img_io.seek(0)
        return SimpleUploadedFile(name="test.jpg", content=img_io.getvalue(), content_type="image/jpeg")

    @staticmethod
    def create_photo(
        image=None,
        original_filename=None,
        **kwargs,
    ):
        from photos.models import Photo

        if image is None:
            image = PhotoFactory.create_test_image()

        photo = Photo(
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
        if date_taken is None:
            date_taken = timezone.make_aware(datetime(2024, 1, 1, 12, 0, 0))

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
        from photos.models import PhotoAlbum

        return PhotoAlbum.objects.create(
            title=title,
            description=description,
            is_private=is_private,
            allow_downloads=allow_downloads,
            slug=slug,
            **kwargs,
        )
