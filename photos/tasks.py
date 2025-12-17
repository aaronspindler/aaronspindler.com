import io
import logging
import zipfile
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger(__name__)

DEBOUNCE_KEY_PREFIX = "album_zip_debounce:"
DEBOUNCE_DELAY_SECONDS = 30


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def schedule_zip_generation(self, album_id: int):
    debounce_key = f"{DEBOUNCE_KEY_PREFIX}{album_id}"

    cache.set(debounce_key, timezone.now().isoformat(), timeout=DEBOUNCE_DELAY_SECONDS + 10)

    generate_album_zip.apply_async(
        args=[album_id],
        countdown=DEBOUNCE_DELAY_SECONDS,
    )

    logger.info(f"Scheduled ZIP generation for album {album_id} in {DEBOUNCE_DELAY_SECONDS}s")


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=1800,
    max_retries=2,
)
def generate_album_zip(self, album_id: int, force: bool = False):
    from photos.models import PhotoAlbum

    debounce_key = f"{DEBOUNCE_KEY_PREFIX}{album_id}"

    try:
        album = PhotoAlbum.objects.get(pk=album_id)
    except PhotoAlbum.DoesNotExist:
        logger.warning(f"Album {album_id} not found for ZIP generation")
        return {"status": "error", "message": "Album not found"}

    if not force:
        last_scheduled = cache.get(debounce_key)
        if last_scheduled:
            try:
                scheduled_time = timezone.datetime.fromisoformat(last_scheduled)
                if timezone.is_naive(scheduled_time):
                    scheduled_time = timezone.make_aware(scheduled_time)
                if timezone.now() < scheduled_time + timedelta(seconds=DEBOUNCE_DELAY_SECONDS - 5):
                    logger.info(f"Skipping ZIP generation for album {album_id} - more changes pending")
                    return {"status": "skipped", "message": "Debounce in progress"}
            except (ValueError, TypeError):
                pass

    if not force and not album.needs_zip_regeneration():
        logger.info(f"Album {album_id} ZIP is up-to-date, skipping")
        return {"status": "skipped", "message": "Content unchanged"}

    if not album.allow_downloads:
        logger.info(f"Album {album_id} has downloads disabled, skipping ZIP")
        return {"status": "skipped", "message": "Downloads disabled"}

    album.zip_generation_status = "generating"
    album.save(update_fields=["zip_generation_status"])

    try:
        zip_buffer = io.BytesIO()
        photos = album.photos.all().order_by("date_taken", "created_at")

        if not photos.exists():
            album.zip_generation_status = "none"
            album.save(update_fields=["zip_generation_status"])
            return {"status": "skipped", "message": "No photos in album"}

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, photo in enumerate(photos, 1):
                image_field = photo.image_optimized or photo.image
                if not image_field:
                    continue

                original_name = photo.original_filename or f"photo_{photo.id}.jpg"
                filename = f"{idx:03d}_{original_name}"

                try:
                    image_field.seek(0)
                    image_data = image_field.read()
                    zf.writestr(filename, image_data)
                except Exception as e:
                    logger.warning(f"Failed to add photo {photo.id} to ZIP: {e}")
                    continue

        if album.zip_file:
            try:
                album.zip_file.delete(save=False)
            except Exception as e:
                logger.warning(f"Failed to delete old ZIP for album {album_id}: {e}")

        zip_buffer.seek(0)
        zip_size = len(zip_buffer.getvalue())
        zip_filename = f"{album.slug}_{timezone.now().strftime('%Y%m%d')}.zip"
        album.zip_file.save(zip_filename, ContentFile(zip_buffer.read()), save=False)

        album.zip_content_hash = album.compute_zip_content_hash()
        album.zip_generated_at = timezone.now()
        album.zip_generation_status = "ready"
        album.zip_file_size = zip_size
        album.save(
            update_fields=[
                "zip_file",
                "zip_content_hash",
                "zip_generated_at",
                "zip_generation_status",
                "zip_file_size",
            ]
        )

        cache.delete(debounce_key)

        logger.info(f"Generated ZIP for album {album_id}: {zip_filename} ({zip_size} bytes)")

        return {
            "status": "success",
            "album_id": album_id,
            "filename": zip_filename,
            "size": zip_size,
            "photo_count": photos.count(),
        }

    except Exception as e:
        logger.error(f"Failed to generate ZIP for album {album_id}: {e}", exc_info=True)
        album.zip_generation_status = "failed"
        album.save(update_fields=["zip_generation_status"])
        raise
