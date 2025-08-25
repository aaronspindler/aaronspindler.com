from django.db import models
from django.core.files.base import ContentFile
from photos.image_utils import ImageOptimizer, ExifExtractor
import os
import json


class Photo(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Original image (full resolution)
    image = models.ImageField(upload_to='photos/full/', verbose_name='Full Resolution')
    
    # Optimized versions
    image_large = models.ImageField(
        upload_to='photos/large/', 
        blank=True, 
        null=True,
        verbose_name='Large (1920px)'
    )
    image_medium = models.ImageField(
        upload_to='photos/medium/', 
        blank=True, 
        null=True,
        verbose_name='Medium (800px)'
    )
    image_small = models.ImageField(
        upload_to='photos/small/', 
        blank=True, 
        null=True,
        verbose_name='Small (400px)'
    )
    image_thumbnail = models.ImageField(
        upload_to='photos/thumbnail/', 
        blank=True, 
        null=True,
        verbose_name='Thumbnail (150px)'
    )
    
    # Metadata
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text='Original file size in bytes')
    width = models.PositiveIntegerField(null=True, blank=True, help_text='Original image width')
    height = models.PositiveIntegerField(null=True, blank=True, help_text='Original image height')
    
    # EXIF Metadata
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
        """
        # Check if this is a new upload or an update to the main image
        try:
            if self.pk is None or (self.pk and self._image_changed()):
                self._process_image()
        except Exception as e:
            # Log the error but don't prevent saving
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
    
    def _process_image(self):
        """
        Process the uploaded image and create optimized versions.
        """
        if not self.image:
            return
        
        # Store original filename
        self.original_filename = os.path.basename(self.image.name)
        
        # Get image dimensions and file size
        from PIL import Image
        img = Image.open(self.image)
        self.width = img.width
        self.height = img.height
        self.file_size = self.image.size
        
        # Extract EXIF data
        self.image.seek(0)  # Reset file pointer before reading EXIF
        exif_data = ExifExtractor.extract_exif(self.image)
        
        # Store EXIF metadata
        if exif_data:
            # Store full EXIF data as JSON (excluding the full_exif for now to avoid serialization issues)
            full_exif = exif_data.pop('full_exif', {})
            
            # Convert full EXIF data to JSON-serializable format
            serializable_exif = {}
            for key, value in full_exif.items():
                try:
                    # Try to serialize the value
                    json.dumps(value)
                    serializable_exif[key] = value
                except (TypeError, ValueError):
                    # If not serializable, convert to string
                    serializable_exif[key] = str(value)
            
            self.exif_data = serializable_exif
            
            # Store individual EXIF fields
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
        
        # Generate optimized versions
        self.image.seek(0)  # Reset file pointer before processing
        variants = ImageOptimizer.process_uploaded_image(self.image, self.original_filename)
        
        # Assign the optimized versions to their respective fields
        if 'large' in variants:
            self.image_large.save(
                variants['large'].name,
                variants['large'],
                save=False
            )
        
        if 'medium' in variants:
            self.image_medium.save(
                variants['medium'].name,
                variants['medium'],
                save=False
            )
        
        if 'small' in variants:
            self.image_small.save(
                variants['small'].name,
                variants['small'],
                save=False
            )
        
        if 'thumbnail' in variants:
            self.image_thumbnail.save(
                variants['thumbnail'].name,
                variants['thumbnail'],
                save=False
            )
        
        # The 'full' variant is now the unmodified original, so we don't need to replace it
        # The original image is already saved as-is
    
    def get_image_url(self, size='medium'):
        """
        Get the URL for a specific image size.
        
        Args:
            size: One of 'thumbnail', 'small', 'medium', 'large', or 'full'
        
        Returns:
            str: URL of the requested image size, or None if not available
        """
        size_field_map = {
            'thumbnail': self.image_thumbnail,
            'small': self.image_small,
            'medium': self.image_medium,
            'large': self.image_large,
            'full': self.image,
        }
        
        image_field = size_field_map.get(size, self.image_medium)
        
        try:
            if image_field:
                return image_field.url
            
            # Fallback to the original image if the requested size doesn't exist
            return self.image.url if self.image else None
        except (ValueError, AttributeError):
            # File doesn't exist or can't generate URL
            return None
    
    def __str__(self):
        return self.title


class PhotoAlbum(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    photos = models.ManyToManyField(Photo, related_name='albums')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Photo Album"
        verbose_name_plural = "Photo Albums"
    
    def __str__(self):
        return self.title