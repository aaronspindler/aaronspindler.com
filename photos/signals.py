import logging

from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.dispatch import receiver

from photos.models import Photo, PhotoAlbum
from photos.tasks import generate_album_zip

logger = logging.getLogger(__name__)


@receiver(m2m_changed, sender=PhotoAlbum.photos.through)
def handle_album_photos_change(sender, instance, action, pk_set=None, **kwargs):
    """
    Trigger zip file regeneration when photos are added or removed from an album.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        if instance.allow_downloads:
            generate_album_zip.delay(instance.pk)
            logger.info(f"Triggered zip regeneration for album {instance.title} after {action}")


@receiver(post_save, sender=PhotoAlbum)
def handle_album_save(sender, instance, created, **kwargs):
    """
    Handle album save events.
    Generate initial zip file for new albums or when downloads are enabled.
    """
    if created and instance.allow_downloads and instance.photos.exists():
        generate_album_zip.delay(instance.pk)
        logger.info(f"Triggered initial zip generation for new album {instance.title}")
    elif not created:
        # Check if downloads were just enabled
        if instance.allow_downloads and instance.photos.exists():
            # Check if we should trigger generation (can't reliably get old state in tests)
            if not instance.zip_file and not instance.zip_file_optimized:
                generate_album_zip.delay(instance.pk)
                logger.info(f"Triggered zip generation for album {instance.title} - downloads enabled")
        elif not instance.allow_downloads:
            # Downloads disabled - clean up zip files
            if instance.zip_file:
                instance.zip_file.delete()
                instance.zip_file = None
            if instance.zip_file_optimized:
                instance.zip_file_optimized.delete()
                instance.zip_file_optimized = None
            # Use update to avoid recursive signal
            PhotoAlbum.objects.filter(pk=instance.pk).update(zip_file=None, zip_file_optimized=None)
            logger.info(f"Deleted zip files for album {instance.title} - downloads disabled")


@receiver(post_save, sender=Photo)
def handle_photo_update(sender, instance, created, **kwargs):
    """
    Regenerate zip files for all albums containing this photo when the photo is updated.
    """
    if not created:
        albums = instance.albums.filter(allow_downloads=True)
        for album in albums:
            generate_album_zip.delay(album.pk)
            logger.info(f"Triggered zip regeneration for album {album.title} due to photo {instance.pk} update")


@receiver(pre_delete, sender=Photo)
def handle_photo_delete(sender, instance, **kwargs):
    """
    Regenerate zip files for all albums that contained this photo before deletion.
    Note: This runs before the photo is actually deleted from the database.
    """
    # Get albums before the photo is deleted from database
    albums = instance.albums.filter(allow_downloads=True)
    album_ids = list(albums.values_list("pk", flat=True))
    for album_id in album_ids:
        generate_album_zip.apply_async(args=[album_id], countdown=2)
        logger.info(f"Scheduled zip regeneration for album {album_id} after photo deletion")
