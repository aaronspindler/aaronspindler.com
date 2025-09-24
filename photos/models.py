from django.db import models
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from config.storage_backends import PrivateMediaStorage
from photos.image_utils import (
    ImageOptimizer, 
    ExifExtractor, 
    DuplicateDetector,
    ImageMetadataExtractor
)
import os

private_storage = PrivateMediaStorage()


class Photo(models.Model):
    title = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True)
    
    image = models.ImageField(upload_to='photos/original/', verbose_name='Original Full Resolution')
    
    image_optimized = models.ImageField(
        upload_to='photos/optimized/', 
        blank=True, 
        null=True,
        verbose_name='Optimized Full Size'
    )
    
    image_display = models.ImageField(
        upload_to='photos/display/', 
        blank=True, 
        null=True,
        verbose_name='Display Version (Smart Cropped)'
    )
    
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text='Original file size in bytes')
    width = models.PositiveIntegerField(null=True, blank=True, help_text='Original image width')
    height = models.PositiveIntegerField(null=True, blank=True, help_text='Original image height')
    
    file_hash = models.CharField(
        max_length=64, 
        blank=True, 
        db_index=True,
        help_text='SHA-256 hash of the original file for exact duplicate detection'
    )
    perceptual_hash = models.CharField(
        max_length=64, 
        blank=True, 
        db_index=True,
        help_text='Perceptual hash for similar image detection'
    )
    
    focal_point_x = models.FloatField(
        null=True, blank=True,
        help_text='X coordinate of focal point (0-1)'
    )
    focal_point_y = models.FloatField(
        null=True, blank=True,
        help_text='Y coordinate of focal point (0-1)'
    )
    
    exif_data = models.JSONField(null=True, blank=True, help_text='Full EXIF data as JSON')
    camera_make = models.CharField(max_length=100, blank=True, help_text='Camera manufacturer')
    camera_model = models.CharField(max_length=100, blank=True, help_text='Camera model')
    lens_model = models.CharField(max_length=100, blank=True, help_text='Lens model')
    focal_length = models.CharField(max_length=50, blank=True, help_text='Focal length (e.g., "50mm")')
    aperture = models.CharField(max_length=50, blank=True, help_text='Aperture (e.g., "f/2.8")')
    shutter_speed = models.CharField(max_length=50, blank=True, help_text='Shutter speed (e.g., "1/250")')
    iso = models.PositiveIntegerField(null=True, blank=True, help_text='ISO value')
    date_taken = models.DateTimeField(null=True, blank=True, help_text='Date photo was taken')
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, help_text='GPS latitude')
    gps_longitude = models.DecimalField(max_digits=11, decimal_places=7, null=True, blank=True, help_text='GPS longitude')
    gps_altitude = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='GPS altitude in meters')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Photo"
        verbose_name_plural = "Photos"
    
    def save(self, *args, **kwargs):
        """
        Override save to automatically create optimized versions when a new image is uploaded.
        Also checks for duplicates before saving.
        """
        try:
            if self.pk is None or (self.pk and self._image_changed()):
                skip_duplicate_check = kwargs.pop('skip_duplicate_check', False)
                
                if not skip_duplicate_check:
                    self._check_for_duplicates()
                
                self._process_image()
        except ValidationError:
            raise
        except Exception as e:
            print(f"Error processing image: {e}")
        
        super().save(*args, **kwargs)
    
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
        
        duplicates = DuplicateDetector.find_duplicates(
            self.image,
            existing_photos,
            exact_match_only=False
        )
        
        # Store computed hashes for reuse
        if duplicates['file_hash']:
            self.file_hash = duplicates['file_hash']
        if duplicates['perceptual_hash']:
            self.perceptual_hash = duplicates['perceptual_hash']
        if duplicates['exact_duplicates']:
            duplicate = duplicates['exact_duplicates'][0]
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
            self.file_hash = hashes['file_hash'] or ''
            self.perceptual_hash = hashes['perceptual_hash'] or ''
        
        self.original_filename = os.path.basename(self.image.name)
        metadata = ImageMetadataExtractor.extract_basic_metadata(self.image)
        self.width = metadata['width']
        self.height = metadata['height']
        self.file_size = metadata['file_size']
        
        self.image.seek(0)  # Reset file pointer before reading EXIF
        exif_data = ExifExtractor.extract_exif(self.image)
        
        if exif_data:
            full_exif = exif_data.pop('full_exif', {})
            serializable_exif = ExifExtractor.make_exif_serializable(full_exif)
            
            self.exif_data = serializable_exif
            self.camera_make = exif_data.get('camera_make', '')
            self.camera_model = exif_data.get('camera_model', '')
            self.lens_model = exif_data.get('lens_model', '')
            self.focal_length = exif_data.get('focal_length', '')
            self.aperture = exif_data.get('aperture', '')
            self.shutter_speed = exif_data.get('shutter_speed', '')
            self.iso = exif_data.get('iso')
            self.date_taken = exif_data.get('date_taken')
            self.gps_latitude = exif_data.get('gps_latitude')
            self.gps_longitude = exif_data.get('gps_longitude')
            self.gps_altitude = exif_data.get('gps_altitude')
        
        self.image.seek(0)  # Reset file pointer before processing
        variants, focal_point = ImageOptimizer.process_uploaded_image(self.image, self.original_filename)
        
        if focal_point:
            self.focal_point_x = focal_point[0]
            self.focal_point_y = focal_point[1]
        if 'optimized' in variants:
            self.image_optimized.save(
                variants['optimized'].name,
                variants['optimized'],
                save=False
            )
        
        if 'display' in variants:
            self.image_display.save(
                variants['display'].name,
                variants['display'],
                save=False
            )
        
    
    def get_image_url(self, size='display'):
        """
        Get the URL for a specific image size.
        
        Args:
            size: One of 'display', 'optimized', or 'original'
        
        Returns:
            str: URL of the requested image size, or None if not available
        """
        size_field_map = {
            'display': self.image_display,
            'optimized': self.image_optimized,
            'original': self.image,
        }
        
        image_field = size_field_map.get(size, self.image_display)
        
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
        other_photos = Photo.objects.exclude(pk=self.pk).exclude(
            perceptual_hash__isnull=True
        ).exclude(perceptual_hash='')
        
        for photo in other_photos:
            is_similar, distance = DuplicateDetector.compare_hashes(
                self.perceptual_hash,
                photo.perceptual_hash,
                threshold=threshold
            )
            if is_similar:
                similar.append((photo, distance))
        
        similar.sort(key=lambda x: x[1])  # Sort by distance (most similar first)
        return similar
    
    def __str__(self):
        if self.title:
            return self.title
        elif self.original_filename:
            return self.original_filename
        else:
            return f"Photo {self.pk}"


class PhotoAlbum(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    photos = models.ManyToManyField(Photo, related_name='albums')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    is_private = models.BooleanField(default=False)
    
    allow_downloads = models.BooleanField(default=False)
    
    zip_file = models.FileField(
        upload_to='albums/zips/original/',
        storage=private_storage,
        blank=True,
        null=True,
        help_text='Zip file containing original quality photos'
    )
    zip_file_optimized = models.FileField(
        upload_to='albums/zips/optimized/',
        storage=private_storage,
        blank=True,
        null=True,
        help_text='Zip file containing optimized quality photos'
    )
    
    class Meta:
        verbose_name = "Photo Album"
        verbose_name_plural = "Photo Albums"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            original_slug = self.slug
            counter = 1
            while PhotoAlbum.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)
    
    def get_download_url(self, quality='optimized'):
        """
        Get a secure download URL for the album zip file.
        
        Args:
            quality: 'original' or 'optimized' (default)
            
        Returns:
            str: Secure URL for downloading the zip file, or None if not available
        """
        if not self.allow_downloads:
            return None
        
        if quality == 'original' and self.zip_file:
            try:
                return self.zip_file.url
            except (ValueError, AttributeError):
                return None
        elif quality == 'optimized' and self.zip_file_optimized:
            try:
                return self.zip_file_optimized.url
            except (ValueError, AttributeError):
                return None
        
        return None
    
    def regenerate_zip_files(self, async_task=True):
        """
        Regenerate the zip files for this album.
        
        Args:
            async_task: If True, use Celery async task. If False, run synchronously.
        """
        from photos.tasks import generate_album_zip
        
        if async_task:
            return generate_album_zip.delay(self.pk)
        else:
            return generate_album_zip(self.pk)
    
    def __str__(self):
        return self.title if self.title else f"Album {self.pk}"