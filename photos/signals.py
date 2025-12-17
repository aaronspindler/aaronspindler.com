import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from photos.models import AlbumPhoto, PhotoAlbum

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AlbumPhoto)
@receiver(post_delete, sender=AlbumPhoto)
def album_photo_changed(sender, instance, **kwargs):
    album = instance.album
    if not album.allow_downloads:
        return

    from photos.tasks import schedule_zip_generation

    logger.info(f"Album {album.id} photos changed, scheduling ZIP regeneration")

    album.zip_generation_status = "pending"
    album.save(update_fields=["zip_generation_status"])

    schedule_zip_generation.delay(album.id)


@receiver(post_save, sender=PhotoAlbum)
def album_downloads_setting_changed(sender, instance, **kwargs):
    if not kwargs.get("update_fields"):
        return

    if "allow_downloads" not in kwargs["update_fields"]:
        return

    from photos.tasks import schedule_zip_generation

    if instance.allow_downloads:
        if instance.photos.exists():
            logger.info(f"Album {instance.id} downloads enabled, scheduling ZIP generation")
            instance.zip_generation_status = "pending"
            instance.save(update_fields=["zip_generation_status"])
            schedule_zip_generation.delay(instance.id)
    else:
        if instance.zip_file:
            logger.info(f"Album {instance.id} downloads disabled, removing ZIP")
            try:
                instance.zip_file.delete(save=False)
            except Exception:
                pass
            instance.zip_file = None
            instance.zip_content_hash = ""
            instance.zip_generation_status = "none"
            instance.zip_generated_at = None
            instance.zip_file_size = None
            instance.save(
                update_fields=[
                    "zip_file",
                    "zip_content_hash",
                    "zip_generation_status",
                    "zip_generated_at",
                    "zip_file_size",
                ]
            )
