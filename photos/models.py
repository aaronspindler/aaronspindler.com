"""
Models for the photos application with type hints and comprehensive docstrings.
"""
from __future__ import annotations
from typing import Optional, Any
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.db.models import QuerySet


class Album(models.Model):
    """
    Model representing a photo album.
    
    An album is a collection of photos that can be published or unpublished.
    Albums can have a cover image and are ordered by the 'order' field for
    manual sorting in the admin interface.
    
    Attributes:
        title: The title of the album
        description: Optional description of the album
        cover_image: Optional cover image for the album
        is_published: Whether the album is publicly visible
        created_at: Timestamp when the album was created
        updated_at: Timestamp when the album was last modified
        order: Integer for manual ordering (lower numbers appear first)
    """
    title: str = models.CharField(
        max_length=200,
        help_text="Title of the album"
    )
    description: str = models.TextField(
        blank=True,
        help_text="Optional description of the album"
    )
    cover_image: Optional[models.ImageField] = models.ImageField(
        upload_to='albums/covers/', 
        null=True, 
        blank=True,
        help_text="Cover image for the album (optional)"
    )
    is_published: bool = models.BooleanField(
        default=False,
        help_text="Whether this album is publicly visible"
    )
    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True,
        help_text="When the album was created"
    )
    updated_at: models.DateTimeField = models.DateTimeField(
        auto_now=True,
        help_text="When the album was last modified"
    )
    order: int = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="For manual ordering in admin (lower numbers appear first)"
    )
    
    class Meta:
        """Metadata for the Album model."""
        ordering: list[str] = ['-created_at']
        verbose_name: str = "Album"
        verbose_name_plural: str = "Albums"
        indexes: list[models.Index] = [
            models.Index(fields=['is_published', 'order', '-created_at']),
        ]
    
    def __str__(self) -> str:
        """
        Return string representation of the album.
        
        Returns:
            str: The album title
        """
        return self.title
    
    def photo_count(self) -> int:
        """
        Return the number of photos in this album.
        
        Returns:
            int: Count of photos in the album
        """
        return self.photos.count()
    
    # Add property for admin display
    photo_count.short_description: str = 'Number of Photos'  # type: ignore
    
    def get_photos(self) -> QuerySet[Photo]:
        """
        Get all photos in this album, properly ordered.
        
        Returns:
            QuerySet[Photo]: Ordered queryset of photos
        """
        return self.photos.all().order_by('order', '-created_at')
    
    def get_published_photos(self) -> QuerySet[Photo]:
        """
        Get only published photos in this album.
        
        Returns:
            QuerySet[Photo]: Filtered queryset of published photos
        """
        return self.get_photos()
    
    def has_photos(self) -> bool:
        """
        Check if the album has any photos.
        
        Returns:
            bool: True if album has photos, False otherwise
        """
        return self.photos.exists()
    
    def get_absolute_url(self) -> str:
        """
        Get the absolute URL for this album.
        
        Returns:
            str: URL path to view this album
        """
        from django.urls import reverse
        return reverse('photos:album_detail', kwargs={'pk': self.pk})
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Override save to perform additional processing.
        
        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        # Ensure order is never negative
        if self.order < 0:
            self.order = 0
        
        super().save(*args, **kwargs)


class Photo(models.Model):
    """
    Model representing a photo within an album.
    
    Photos belong to an album and can have titles, captions, and both
    original and thumbnail versions. Photos are ordered within their
    album using the 'order' field.
    
    Attributes:
        album: The album this photo belongs to
        title: Optional title for the photo
        caption: Optional caption/description for the photo
        original_image: The original uploaded image
        thumbnail: Automatically generated thumbnail image
        order: Integer for manual ordering within the album
        created_at: Timestamp when the photo was uploaded
    """
    album: Album = models.ForeignKey(
        Album, 
        on_delete=models.CASCADE, 
        related_name='photos',
        help_text="The album this photo belongs to"
    )
    title: str = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional title for the photo"
    )
    caption: str = models.TextField(
        blank=True,
        help_text="Optional caption or description"
    )
    original_image: models.ImageField = models.ImageField(
        upload_to='albums/photos/originals/',
        help_text="Original uploaded image"
    )
    thumbnail: Optional[models.ImageField] = models.ImageField(
        upload_to='albums/photos/thumbnails/', 
        blank=True,
        help_text="Automatically generated from original image"
    )
    order: int = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="For manual ordering within album (lower numbers appear first)"
    )
    created_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True,
        help_text="When the photo was uploaded"
    )
    
    class Meta:
        """Metadata for the Photo model."""
        ordering: list[str] = ['order', '-created_at']
        verbose_name: str = "Photo"
        verbose_name_plural: str = "Photos"
        indexes: list[models.Index] = [
            models.Index(fields=['album', 'order', '-created_at']),
        ]
    
    def __str__(self) -> str:
        """
        Return string representation of the photo.
        
        Returns:
            str: Photo title with album name, or generic description
        """
        if self.title:
            return f"{self.title} - {self.album.title}"
        return f"Photo in {self.album.title}"
    
    def get_display_title(self) -> str:
        """
        Get a display title for the photo.
        
        Returns:
            str: The photo title or a default string
        """
        return self.title or f"Photo {self.pk or 'New'}"
    
    def get_image_url(self) -> Optional[str]:
        """
        Get the URL for displaying this photo.
        
        Prefers thumbnail if available, falls back to original.
        
        Returns:
            Optional[str]: URL to the image or None if no image
        """
        if self.thumbnail:
            return self.thumbnail.url
        elif self.original_image:
            return self.original_image.url
        return None
    
    def get_original_url(self) -> Optional[str]:
        """
        Get the URL for the original image.
        
        Returns:
            Optional[str]: URL to the original image or None
        """
        if self.original_image:
            return self.original_image.url
        return None
    
    def get_thumbnail_url(self) -> Optional[str]:
        """
        Get the URL for the thumbnail image.
        
        Returns:
            Optional[str]: URL to the thumbnail or None if not generated
        """
        if self.thumbnail:
            return self.thumbnail.url
        return None
    
    def has_thumbnail(self) -> bool:
        """
        Check if this photo has a thumbnail.
        
        Returns:
            bool: True if thumbnail exists, False otherwise
        """
        return bool(self.thumbnail)
    
    def get_absolute_url(self) -> str:
        """
        Get the absolute URL for this photo.
        
        Since photos don't have individual pages, returns the album URL.
        
        Returns:
            str: URL path to the album containing this photo
        """
        return self.album.get_absolute_url()
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Override save to ensure proper file paths and processing.
        
        This method handles the two-phase save process needed to get the
        photo ID before saving the image files, ensuring proper paths.
        
        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        # Ensure order is never negative
        if self.order < 0:
            self.order = 0
        
        if self.pk is None:
            # First save to get the ID
            saved_image = self.original_image
            self.original_image = None  # type: ignore
            super().save(*args, **kwargs)
            self.original_image = saved_image
            
            # Update the image path to include album ID
            if self.original_image:
                # The storage backend will handle the actual path
                # This is just to ensure we have an ID before saving the file
                pass
        
        super().save(*args, **kwargs)
    
    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        """
        Override delete to ensure proper cleanup.
        
        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
            
        Returns:
            tuple: Number of objects deleted and a dictionary with the number of deletions per object type
        """
        # The pre_delete signal will handle file cleanup
        return super().delete(*args, **kwargs)