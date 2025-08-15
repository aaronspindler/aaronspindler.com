from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.core.files.base import ContentFile
from .image_utils import ImageOptimizer
import os

class PageVisit(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField()
    page_name = models.CharField(max_length=255)
    geo_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.page_name} visited from {self.ip_address} at {self.created_at}"

    class Meta:
        verbose_name = "Page Visit"
        verbose_name_plural = "Page Visits"
        
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
        if self.pk is None or (self.pk and self._image_changed()):
            self._process_image()
        
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
        
        # Generate optimized versions
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
        
        if image_field:
            return image_field.url
        
        # Fallback to the original image if the requested size doesn't exist
        return self.image.url if self.image else None
    
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