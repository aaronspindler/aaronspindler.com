from io import BytesIO
from unittest.mock import MagicMock

from PIL import Image


def create_tiny_test_image(size=(10, 10), color="blue", format="JPEG"):
    img = Image.new("RGB", size, color=color)
    img_io = BytesIO()
    img.save(img_io, format=format, quality=50)
    img_io.seek(0)
    return img_io


def mock_image_optimizer_process():
    mock_preview = MagicMock(name="preview.jpg")
    mock_thumbnail = MagicMock(name="thumbnail.jpg")
    return (
        {"preview": mock_preview, "thumbnail": mock_thumbnail},
        (0.5, 0.5),  # focal point
        None,  # saliency_map_bytes
    )


def mock_duplicate_detector_hashes(identifier="test"):
    return {"file_hash": f"hash_{identifier}", "perceptual_hash": f"phash_{identifier}"}


def mock_exif_extractor_data(basic=True):
    if basic:
        return {}

    return {
        "camera_make": "Canon",
        "camera_model": "EOS R5",
        "iso": 400,
        "aperture": "f/2.8",
        "shutter_speed": "1/250",
        "focal_length": "50mm",
        "date_taken": None,
        "full_exif": {},
    }


def mock_image_metadata(width=10, height=10, file_size=1024):
    return {
        "width": width,
        "height": height,
        "file_size": file_size,
        "format": "JPEG",
        "mode": "RGB",
    }


class PhotoTestMixin:
    @staticmethod
    def create_mock_photo_with_minimal_processing(filename="test_photo.jpg"):
        from unittest.mock import patch

        from django.core.files.uploadedfile import SimpleUploadedFile

        from photos.models import Photo

        img_io = create_tiny_test_image()
        test_image = SimpleUploadedFile(
            name=filename,
            content=img_io.getvalue(),
            content_type="image/jpeg",
        )

        with (
            patch("photos.models.ImageOptimizer.process_uploaded_image") as mock_process,
            patch("photos.models.DuplicateDetector.compute_and_store_hashes") as mock_hashes,
            patch("photos.models.ExifExtractor.extract_exif") as mock_exif,
            patch("photos.models.ImageMetadataExtractor.extract_basic_metadata") as mock_metadata,
        ):
            mock_process.return_value = mock_image_optimizer_process()
            mock_hashes.return_value = mock_duplicate_detector_hashes(filename)
            mock_exif.return_value = mock_exif_extractor_data()
            mock_metadata.return_value = mock_image_metadata()

            photo = Photo(image=test_image)
            photo.save(skip_duplicate_check=True)
            return photo
