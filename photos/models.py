import os
import uuid

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from photos.image_utils import DuplicateDetector, ExifExtractor, ImageMetadataExtractor, ImageOptimizer


def photo_upload_to(instance, filename):
    """Generate upload path for original photos using UUID."""
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"photos/original/{instance.uuid}{ext}"


def thumbnail_upload_to(instance, filename):
    """Generate upload path for thumbnails using UUID."""
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"photos/thumbnails/{instance.uuid}_thumbnail{ext}"


def preview_upload_to(instance, filename):
    """Generate upload path for previews using UUID."""
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"photos/preview/{instance.uuid}_preview{ext}"


def saliency_upload_to(instance, _filename):
    """Generate upload path for saliency maps using UUID."""
    return f"photos/saliency/{instance.uuid}_saliency.png"


class Photo(models.Model):
    PROCESSING_STATUS_CHOICES = [
        ("pending", "Pending Processing"),
        ("processing", "Processing"),
        ("complete", "Complete"),
        ("failed", "Failed"),
    ]

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    image = models.ImageField(upload_to=photo_upload_to, verbose_name="Original Full Resolution")

    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default="pending",
        db_index=True,
        help_text="Status of background image processing",
    )

    image_thumbnail = models.ImageField(
        upload_to=thumbnail_upload_to,
        blank=True,
        null=True,
        verbose_name="Thumbnail Version (Smart Cropped)",
    )

    image_preview = models.ImageField(
        upload_to=preview_upload_to,
        blank=True,
        null=True,
        verbose_name="Preview Version (Full Size, Highly Compressed)",
    )

    saliency_map = models.ImageField(
        upload_to=saliency_upload_to,
        blank=True,
        null=True,
        verbose_name="Saliency Map (Debug Visualization)",
        help_text="Visualization of saliency detection algorithm for debugging smart crop",
    )

    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="Original file size in bytes")
    width = models.PositiveIntegerField(null=True, blank=True, help_text="Original image width")
    height = models.PositiveIntegerField(null=True, blank=True, help_text="Original image height")

    file_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="SHA-256 hash of the original file for exact duplicate detection",
    )
    perceptual_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="Perceptual hash for similar image detection",
    )

    focal_point_x = models.FloatField(null=True, blank=True, help_text="X coordinate of focal point (0-1)")
    focal_point_y = models.FloatField(null=True, blank=True, help_text="Y coordinate of focal point (0-1)")
    focal_point_override = models.BooleanField(
        default=False,
        help_text="When enabled, prevents automatic focal point detection from overwriting the current focal point values",
    )

    exif_data = models.JSONField(null=True, blank=True, help_text="Full EXIF data as JSON")
    camera_make = models.CharField(max_length=100, blank=True, help_text="Camera manufacturer")
    camera_model = models.CharField(max_length=100, blank=True, help_text="Camera model")
    lens_model = models.CharField(max_length=100, blank=True, help_text="Lens model")
    focal_length = models.CharField(max_length=50, blank=True, help_text='Focal length (e.g., "50mm")')
    aperture = models.CharField(max_length=50, blank=True, help_text='Aperture (e.g., "f/2.8")')
    shutter_speed = models.CharField(max_length=50, blank=True, help_text='Shutter speed (e.g., "1/250")')
    iso = models.PositiveIntegerField(null=True, blank=True, help_text="ISO value")
    date_taken = models.DateTimeField(null=True, blank=True, help_text="Date photo was taken")
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, help_text="GPS latitude")
    gps_longitude = models.DecimalField(
        max_digits=11,
        decimal_places=7,
        null=True,
        blank=True,
        help_text="GPS longitude",
    )
    gps_altitude = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="GPS altitude in meters",
    )

    # PostgreSQL full-text search vector
    search_vector = SearchVectorField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Photo"
        verbose_name_plural = "Photos"
        indexes = [
            GinIndex(fields=["search_vector"], name="photo_search_idx"),
        ]

    def save(self, *args, **kwargs):
        """
        Override save to automatically create optimized versions when a new image is uploaded.
        Also checks for duplicates before saving.

        Kwargs:
            skip_duplicate_check: Skip duplicate detection (already checked).
            skip_processing: Skip image processing (will be done async).
        """
        skip_processing = kwargs.pop("skip_processing", False)

        try:
            if self.pk is None or (self.pk and self._image_changed()):
                skip_duplicate_check = kwargs.pop("skip_duplicate_check", False)

                if not skip_duplicate_check:
                    self._check_for_duplicates()

                if skip_processing:
                    self.processing_status = "pending"
                else:
                    self._process_image()
        except ValidationError:
            raise
        except Exception as e:
            print(f"Error processing image: {e}")

        super().save(*args, **kwargs)

    def save_minimal(self, file_hash="", perceptual_hash=""):
        """
        Save the photo with minimal processing for async background processing.
        Only stores the original filename and hashes, queues background processing.

        Args:
            file_hash: Pre-computed SHA-256 hash of the file.
            perceptual_hash: Pre-computed perceptual hash.
        """
        if self.image:
            self.original_filename = os.path.basename(self.image.name)
        self.file_hash = file_hash
        self.perceptual_hash = perceptual_hash
        self.processing_status = "pending"
        self.save(skip_duplicate_check=True, skip_processing=True)

    def process_image_async(self):
        """
        Process the image (extract metadata, create optimized versions).
        Called by the Celery background task.
        """
        if not self.image:
            return

        self.processing_status = "processing"
        self.save(update_fields=["processing_status"])

        try:
            self._process_image()
            self.processing_status = "complete"
            self.save()
        except Exception as e:
            self.processing_status = "failed"
            self.save(update_fields=["processing_status"])
            raise e

    def _image_changed(self):
        """
        Check if the main image has changed.
        """
        if not self.pk:
            return True

        try:
            old_instance = Photo.objects.get(pk=self.pk)
            return old_instance.image != self.image
        except Photo.DoesNotExist:
            return True

    def _check_for_duplicates(self):
        """
        Check if the uploaded image is a duplicate of an existing image.
        Raises ValidationError if an exact duplicate is found.
        """
        if not self.image:
            return

        existing_photos = Photo.objects.all()
        if self.pk:
            existing_photos = existing_photos.exclude(pk=self.pk)

        duplicates = DuplicateDetector.find_duplicates(self.image, existing_photos, exact_match_only=False)

        # Store computed hashes for reuse
        if duplicates["file_hash"]:
            self.file_hash = duplicates["file_hash"]
        if duplicates["perceptual_hash"]:
            self.perceptual_hash = duplicates["perceptual_hash"]
        if duplicates["exact_duplicates"]:
            duplicate = duplicates["exact_duplicates"][0]
            raise ValidationError(
                f"This image is an exact duplicate of '{duplicate}' "
                f"(uploaded on {duplicate.created_at.strftime('%Y-%m-%d')}). "
                f"The duplicate image was not uploaded."
            )

    def _process_image(self):
        """
        Process the uploaded image and create optimized versions.
        """
        if not self.image:
            return

        if not self.file_hash or not self.perceptual_hash:
            hashes = DuplicateDetector.compute_and_store_hashes(self.image)
            self.file_hash = hashes["file_hash"] or ""
            self.perceptual_hash = hashes["perceptual_hash"] or ""

        self.original_filename = os.path.basename(self.image.name)
        metadata = ImageMetadataExtractor.extract_basic_metadata(self.image)
        self.width = metadata["width"]
        self.height = metadata["height"]
        self.file_size = metadata["file_size"]

        self.image.seek(0)  # Reset file pointer before reading EXIF
        exif_data = ExifExtractor.extract_exif(self.image)

        if exif_data:
            full_exif = exif_data.pop("full_exif", {})
            serializable_exif = ExifExtractor.make_exif_serializable(full_exif)

            self.exif_data = serializable_exif
            self.camera_make = exif_data.get("camera_make", "")
            self.camera_model = exif_data.get("camera_model", "")
            self.lens_model = exif_data.get("lens_model", "")
            self.focal_length = exif_data.get("focal_length", "")
            self.aperture = exif_data.get("aperture", "")
            self.shutter_speed = exif_data.get("shutter_speed", "")
            self.iso = exif_data.get("iso")
            self.date_taken = exif_data.get("date_taken")
            self.gps_latitude = exif_data.get("gps_latitude")
            self.gps_longitude = exif_data.get("gps_longitude")
            self.gps_altitude = exif_data.get("gps_altitude")

        self.image.seek(0)  # Reset file pointer before processing
        original_ext = os.path.splitext(self.original_filename)[1] or ".jpg"

        # If override is enabled, use existing focal point values; otherwise compute new ones
        existing_focal_point = None
        if self.focal_point_override and self.focal_point_x is not None and self.focal_point_y is not None:
            existing_focal_point = (self.focal_point_x, self.focal_point_y)

        variants, focal_point, saliency_map_bytes = ImageOptimizer.process_uploaded_image(
            self.image, str(self.uuid), original_ext, existing_focal_point=existing_focal_point
        )

        # Only update focal point if not using override
        if not self.focal_point_override and focal_point:
            self.focal_point_x = focal_point[0]
            self.focal_point_y = focal_point[1]

        if "thumbnail" in variants:
            self.image_thumbnail.save(variants["thumbnail"].name, variants["thumbnail"], save=False)

        if "preview" in variants:
            self.image_preview.save(variants["preview"].name, variants["preview"], save=False)

        # Save saliency map for debugging (already computed during focal point calculation)
        if saliency_map_bytes:
            import logging

            from django.core.files.base import ContentFile

            logger = logging.getLogger(__name__)
            saliency_filename = f"{self.uuid}_saliency.png"
            self.saliency_map.save(saliency_filename, ContentFile(saliency_map_bytes), save=False)
            logger.info(f"Saved saliency map for photo {self.pk}: {saliency_filename}")
        else:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"No saliency map generated for photo {self.pk} - computation returned None")

    def get_image_url(self, size="thumbnail"):
        """
        Get the URL for a specific image size.

        Args:
            size: One of 'preview', 'thumbnail', or 'original'

        Returns:
            str: URL of the requested image size, or None if not available
        """
        size_field_map = {
            "preview": self.image_preview,
            "thumbnail": self.image_thumbnail,
            "original": self.image,
        }

        image_field = size_field_map.get(size, self.image_thumbnail)

        try:
            if image_field:
                return image_field.url
            return self.image.url if self.image else None
        except (ValueError, AttributeError):
            return None  # File doesn't exist or can't generate URL

    def get_similar_images(self, threshold=5):
        """
        Find images that are visually similar to this one.

        Args:
            threshold: Maximum Hamming distance for similarity (0-10, lower = more strict)

        Returns:
            list: List of (Photo, distance) tuples sorted by similarity
        """
        if not self.perceptual_hash:
            return []

        similar = []
        other_photos = (
            Photo.objects.exclude(pk=self.pk).exclude(perceptual_hash__isnull=True).exclude(perceptual_hash="")
        )

        for photo in other_photos:
            is_similar, distance = DuplicateDetector.compare_hashes(
                self.perceptual_hash, photo.perceptual_hash, threshold=threshold
            )
            if is_similar:
                similar.append((photo, distance))

        similar.sort(key=lambda x: x[1])  # Sort by distance (most similar first)
        return similar

    def __str__(self):
        if self.original_filename:
            return self.original_filename
        else:
            return f"Photo {self.pk}"


class PhotoAlbum(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    photos = models.ManyToManyField(Photo, through="AlbumPhoto", related_name="albums")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_private = models.BooleanField(default=False)

    allow_downloads = models.BooleanField(default=False)

    # External sharing fields
    share_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text="Unique token for sharing this private album externally",
    )
    share_access_count = models.PositiveIntegerField(
        default=0, help_text="Number of times the share link has been accessed"
    )
    share_last_accessed = models.DateTimeField(null=True, blank=True, help_text="Last time the share link was accessed")

    # ZIP download fields
    zip_file = models.FileField(
        upload_to="albums/zips/",
        blank=True,
        null=True,
        help_text="ZIP file containing original photos from this album",
    )
    zip_content_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 hash of photo IDs + file hashes for change detection",
    )
    zip_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the ZIP file was last generated",
    )
    zip_generation_status = models.CharField(
        max_length=20,
        choices=[
            ("none", "Not Generated"),
            ("pending", "Generation Pending"),
            ("generating", "Generating"),
            ("ready", "Ready"),
            ("failed", "Generation Failed"),
        ],
        default="none",
        help_text="Current status of ZIP file generation",
    )
    zip_file_size = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Size of ZIP file in bytes",
    )

    # PostgreSQL full-text search vector
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        verbose_name = "Photo Album"
        verbose_name_plural = "Photo Albums"
        indexes = [
            GinIndex(fields=["search_vector"], name="album_search_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            original_slug = self.slug
            counter = 1
            while PhotoAlbum.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def compute_zip_content_hash(self) -> str:
        import hashlib

        photos = self.photos.order_by("id").values_list("id", "file_hash")
        if not photos:
            return ""

        content_string = "|".join(f"{pid}:{fhash}" for pid, fhash in photos)
        return hashlib.sha256(content_string.encode()).hexdigest()

    def needs_zip_regeneration(self) -> bool:
        if not self.allow_downloads:
            return False
        if not self.photos.exists():
            return False
        current_hash = self.compute_zip_content_hash()
        return current_hash != self.zip_content_hash

    def get_photos_with_featured(self):
        return self.album_photos.select_related("photo").order_by(
            "display_order",
            "-photo__date_taken",
            "-added_at",
        )

    def __str__(self):
        return self.title if self.title else f"Album {self.pk}"


class AlbumPhoto(models.Model):
    album = models.ForeignKey(
        PhotoAlbum,
        on_delete=models.CASCADE,
        related_name="album_photos",
    )
    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        related_name="album_memberships",
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Display this photo at 2x2 size in the grid",
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order within the album (0 = use date_taken order)",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["album", "photo"]]
        ordering = ["display_order", "-photo__date_taken", "-added_at"]
        verbose_name = "Album Photo"
        verbose_name_plural = "Album Photos"

    def __str__(self):
        featured = " (Featured)" if self.is_featured else ""
        return f"{self.photo} in {self.album}{featured}"
