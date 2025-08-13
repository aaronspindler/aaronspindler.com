"""
Django signals for automatic thumbnail generation and S3 cleanup with enhanced logging and type hints.

This module contains signal handlers for the Photo model that:
1. Automatically generate thumbnails when photos are uploaded
2. Clean up S3 files when photos are deleted
3. Set album covers automatically from the first photo
"""
from __future__ import annotations
from typing import Any, Optional, Type
from django.db.models.signals import post_save, pre_delete
from django.db.models import Model
from django.dispatch import receiver
from django.core.files.base import ContentFile
import logging

from .models import Photo, Album
from .utils import generate_thumbnail, get_thumbnail_filename, cleanup_s3_file

# Set up logger
logger = logging.getLogger(__name__)


@receiver(post_save, sender=Photo)
def create_thumbnail(
    sender: Type[Photo],
    instance: Photo,
    created: bool,
    raw: bool = False,
    using: Optional[str] = None,
    update_fields: Optional[set[str]] = None,
    **kwargs: Any
) -> None:
    """
    Automatically generate thumbnail when a new photo is uploaded.
    
    This signal handler is triggered after a Photo instance is saved. It checks
    if this is a new photo with an original image but no thumbnail, and if so,
    generates a thumbnail automatically.
    
    Args:
        sender: The model class (Photo) that sent the signal
        instance: The actual Photo instance being saved
        created: Boolean indicating if this is a new instance
        raw: Boolean indicating if the model is saved exactly as presented
             (usually False, True when loading fixtures)
        using: The database alias being used
        update_fields: The set of fields to update explicitly specified
                      in the save() call, if any
        **kwargs: Additional keyword arguments passed by the signal
    
    Returns:
        None
        
    Note:
        - Only processes newly created photos (created=True)
        - Skips if photo already has a thumbnail
        - Skips if loading from fixtures (raw=True)
        - Uses update() to avoid triggering signals recursively
    """
    # Skip if loading fixtures
    if raw:
        logger.debug(f"Skipping thumbnail generation for Photo {instance.pk} (raw save)")
        return
    
    # Only process if it's a new photo with an original image and no thumbnail yet
    if created and instance.original_image and not instance.thumbnail:
        logger.info(f"Starting thumbnail generation for Photo ID {instance.pk}")
        
        try:
            # Log image details
            image_name = instance.original_image.name if instance.original_image else "unknown"
            logger.debug(f"Processing image: {image_name}")
            
            # Generate thumbnail from original image
            thumbnail_file: Optional[ContentFile] = generate_thumbnail(instance.original_image)
            
            if thumbnail_file:
                # Generate thumbnail filename
                thumb_filename: str = get_thumbnail_filename(instance.original_image.name)
                logger.debug(f"Generated thumbnail filename: {thumb_filename}")
                
                # Save thumbnail to the instance
                instance.thumbnail.save(thumb_filename, thumbnail_file, save=False)
                
                # Update the instance without triggering signals again
                # This prevents infinite recursion
                Photo.objects.filter(pk=instance.pk).update(thumbnail=instance.thumbnail)
                
                logger.info(
                    f"Thumbnail successfully generated for Photo ID {instance.pk}: "
                    f"{thumb_filename}"
                )
            else:
                logger.warning(
                    f"Failed to generate thumbnail for Photo ID {instance.pk}: "
                    f"generate_thumbnail returned None"
                )
                
        except AttributeError as e:
            logger.error(
                f"AttributeError generating thumbnail for Photo ID {instance.pk}: "
                f"Missing required attribute - {str(e)}",
                exc_info=True
            )
        except IOError as e:
            logger.error(
                f"IOError generating thumbnail for Photo ID {instance.pk}: "
                f"File operation failed - {str(e)}",
                exc_info=True
            )
        except Exception as e:
            logger.error(
                f"Unexpected error generating thumbnail for Photo ID {instance.pk}: "
                f"{type(e).__name__}: {str(e)}",
                exc_info=True
            )
    else:
        # Log why we're skipping
        if not created:
            logger.debug(f"Skipping thumbnail generation for Photo ID {instance.pk} (not newly created)")
        elif not instance.original_image:
            logger.debug(f"Skipping thumbnail generation for Photo ID {instance.pk} (no original image)")
        elif instance.thumbnail:
            logger.debug(f"Skipping thumbnail generation for Photo ID {instance.pk} (thumbnail already exists)")


@receiver(pre_delete, sender=Photo)
def delete_photo_files(
    sender: Type[Photo],
    instance: Photo,
    using: Optional[str] = None,
    **kwargs: Any
) -> None:
    """
    Delete associated files from S3 when a Photo is deleted.
    
    This signal handler is triggered before a Photo instance is deleted. It ensures
    that both the original image and thumbnail are removed from S3 storage to
    prevent orphaned files.
    
    Args:
        sender: The model class (Photo) that sent the signal
        instance: The actual Photo instance being deleted
        using: The database alias being used
        **kwargs: Additional keyword arguments passed by the signal
    
    Returns:
        None
        
    Note:
        - Runs before the database record is deleted (pre_delete)
        - Attempts to delete both original and thumbnail images
        - Continues even if one deletion fails
        - Logs all operations for debugging
    """
    photo_id: Optional[int] = instance.pk
    album_name: str = instance.album.title if instance.album else "Unknown Album"
    
    logger.info(f"Starting file cleanup for Photo ID {photo_id} from album '{album_name}'")
    
    # Track cleanup results
    cleanup_results = {
        'original': False,
        'thumbnail': False
    }
    
    # Delete original image from S3
    if instance.original_image:
        try:
            original_name: str = instance.original_image.name
            logger.debug(f"Attempting to delete original image: {original_name}")
            
            success: bool = cleanup_s3_file(instance.original_image)
            cleanup_results['original'] = success
            
            if success:
                logger.info(f"Successfully deleted original image for Photo ID {photo_id}: {original_name}")
            else:
                logger.error(
                    f"Failed to delete original image for Photo ID {photo_id}: {original_name}"
                )
        except Exception as e:
            logger.error(
                f"Exception while deleting original image for Photo ID {photo_id}: "
                f"{type(e).__name__}: {str(e)}",
                exc_info=True
            )
    else:
        logger.debug(f"No original image to delete for Photo ID {photo_id}")
        cleanup_results['original'] = True  # Nothing to delete is considered success
    
    # Delete thumbnail from S3
    if instance.thumbnail:
        try:
            thumbnail_name: str = instance.thumbnail.name
            logger.debug(f"Attempting to delete thumbnail: {thumbnail_name}")
            
            success = cleanup_s3_file(instance.thumbnail)
            cleanup_results['thumbnail'] = success
            
            if success:
                logger.info(f"Successfully deleted thumbnail for Photo ID {photo_id}: {thumbnail_name}")
            else:
                logger.error(
                    f"Failed to delete thumbnail for Photo ID {photo_id}: {thumbnail_name}"
                )
        except Exception as e:
            logger.error(
                f"Exception while deleting thumbnail for Photo ID {photo_id}: "
                f"{type(e).__name__}: {str(e)}",
                exc_info=True
            )
    else:
        logger.debug(f"No thumbnail to delete for Photo ID {photo_id}")
        cleanup_results['thumbnail'] = True  # Nothing to delete is considered success
    
    # Log summary
    if all(cleanup_results.values()):
        logger.info(f"Successfully completed all file cleanup for Photo ID {photo_id}")
    else:
        failed_items = [k for k, v in cleanup_results.items() if not v]
        logger.warning(
            f"Partial file cleanup for Photo ID {photo_id}. "
            f"Failed to delete: {', '.join(failed_items)}"
        )


@receiver(post_save, sender=Photo)
def update_album_cover(
    sender: Type[Photo],
    instance: Photo,
    created: bool,
    raw: bool = False,
    using: Optional[str] = None,
    update_fields: Optional[set[str]] = None,
    **kwargs: Any
) -> None:
    """
    Automatically set album cover to first photo if no cover is set.
    
    This signal handler ensures that albums always have a cover image by
    automatically using the first photo added to an album as its cover
    if no cover has been explicitly set.
    
    Args:
        sender: The model class (Photo) that sent the signal
        instance: The actual Photo instance being saved
        created: Boolean indicating if this is a new instance
        raw: Boolean indicating if the model is saved exactly as presented
        using: The database alias being used
        update_fields: The set of fields to update explicitly specified
                      in the save() call, if any
        **kwargs: Additional keyword arguments passed by the signal
    
    Returns:
        None
        
    Note:
        - Only runs for newly created photos
        - Only sets cover if album doesn't already have one
        - Prefers thumbnail over original image for performance
        - Uses update_fields to minimize database writes
    """
    # Skip if loading fixtures
    if raw:
        logger.debug(f"Skipping album cover update for Photo {instance.pk} (raw save)")
        return
    
    # Only process newly created photos with an associated album
    if created and instance.album and not instance.album.cover_image:
        album: Album = instance.album
        photo_count: int = album.photos.count()
        
        logger.debug(
            f"Checking album cover for Album ID {album.pk} "
            f"('{album.title}') with {photo_count} photos"
        )
        
        # Check if this is the first photo in the album
        if photo_count == 1:
            try:
                # Use the thumbnail as the album cover if available
                if instance.thumbnail:
                    album.cover_image = instance.thumbnail
                    logger.info(
                        f"Setting album cover for Album ID {album.pk} "
                        f"to thumbnail of Photo ID {instance.pk}"
                    )
                else:
                    album.cover_image = instance.original_image
                    logger.info(
                        f"Setting album cover for Album ID {album.pk} "
                        f"to original image of Photo ID {instance.pk} (no thumbnail available)"
                    )
                
                # Save only the cover_image field to avoid unnecessary updates
                album.save(update_fields=['cover_image'])
                
                logger.info(
                    f"Successfully set album cover for Album '{album.title}' "
                    f"(ID: {album.pk}) using Photo ID {instance.pk}"
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to set album cover for Album ID {album.pk}: "
                    f"{type(e).__name__}: {str(e)}",
                    exc_info=True
                )
        else:
            logger.debug(
                f"Album ID {album.pk} already has {photo_count} photos, "
                f"not updating cover"
            )
    else:
        # Log why we're skipping
        if not created:
            logger.debug(f"Skipping album cover update for Photo ID {instance.pk} (not newly created)")
        elif not instance.album:
            logger.debug(f"Skipping album cover update for Photo ID {instance.pk} (no album associated)")
        elif instance.album.cover_image:
            logger.debug(
                f"Skipping album cover update for Photo ID {instance.pk} "
                f"(album already has cover)"
            )


def disconnect_signals() -> None:
    """
    Disconnect all signals for this module.
    
    Useful for testing or when you want to handle operations manually
    without automatic signal processing.
    
    Returns:
        None
    """
    logger.info("Disconnecting photo signals")
    
    post_save.disconnect(create_thumbnail, sender=Photo)
    post_save.disconnect(update_album_cover, sender=Photo)
    pre_delete.disconnect(delete_photo_files, sender=Photo)
    
    logger.info("Photo signals disconnected")


def reconnect_signals() -> None:
    """
    Reconnect all signals for this module.
    
    Use this after disconnect_signals() to restore normal functionality.
    
    Returns:
        None
    """
    logger.info("Reconnecting photo signals")
    
    post_save.connect(create_thumbnail, sender=Photo)
    post_save.connect(update_album_cover, sender=Photo)
    pre_delete.connect(delete_photo_files, sender=Photo)
    
    logger.info("Photo signals reconnected")