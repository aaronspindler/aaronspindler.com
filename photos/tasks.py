import logging
import os
import shutil
import tempfile
import zipfile
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.core.files import File
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def process_photo_async(self, photo_id: int, force: bool = False):
    """
    Process a photo in the background: extract metadata, create optimized versions.

    Args:
        photo_id: The ID of the Photo to process.
        force: If True, reprocess even if already complete.

    Returns:
        dict: Result containing status and photo_id.
    """
    from photos.models import Photo

    try:
        photo = Photo.objects.get(pk=photo_id)
    except Photo.DoesNotExist:
        logger.warning(f"Photo {photo_id} not found for processing")
        return {"status": "error", "message": "Photo not found", "photo_id": photo_id}

    if not force and photo.processing_status == "complete":
        logger.info(f"Photo {photo_id} already processed, skipping")
        return {"status": "skipped", "message": "Already processed", "photo_id": photo_id}

    try:
        photo.process_image_async()
        logger.info(f"Successfully processed photo {photo_id}")
        return {"status": "success", "photo_id": photo_id}
    except Exception as e:
        logger.error(f"Failed to process photo {photo_id}: {e}", exc_info=True)
        raise


DEBOUNCE_KEY_PREFIX = "album_zip_debounce:"
DEBOUNCE_DELAY_SECONDS = 30
STREAM_CHUNK_SIZE = 8 * 1024 * 1024  # 8MB chunks


def _stream_file_to_zip(zf: zipfile.ZipFile, file_field, zip_path: str, photo_id: int) -> bool:
    """
    Stream a file from storage directly into a ZIP archive.

    Uses a temporary file to avoid loading the entire image into memory.
    Returns True if successful, False otherwise.
    """
    temp_path = None
    try:
        with file_field.open("rb") as src:
            fd, temp_path = tempfile.mkstemp()
            try:
                with os.fdopen(fd, "wb") as dst:
                    shutil.copyfileobj(src, dst, length=STREAM_CHUNK_SIZE)
            except Exception:
                os.close(fd)
                raise

        zf.write(temp_path, zip_path)
        return True
    except Exception as e:
        logger.warning(f"Failed to add photo {photo_id} to ZIP at {zip_path}: {e}")
        return False
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


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
            except (ValueError, TypeError) as e:
                logger.warning(
                    "Invalid debounce timestamp %r for album %s: %s",
                    last_scheduled,
                    album_id,
                    e,
                )

    if not force and not album.needs_zip_regeneration():
        logger.info(f"Album {album_id} ZIP is up-to-date, skipping")
        return {"status": "skipped", "message": "Content unchanged"}

    if not album.allow_downloads:
        logger.info(f"Album {album_id} has downloads disabled, skipping ZIP")
        return {"status": "skipped", "message": "Downloads disabled"}

    album.zip_generation_status = "generating"
    album.save(update_fields=["zip_generation_status"])

    temp_zip_path = None
    try:
        photos = album.photos.all().order_by("date_taken", "created_at")

        if not photos.exists():
            album.zip_generation_status = "none"
            album.save(update_fields=["zip_generation_status"])
            return {"status": "skipped", "message": "No photos in album"}

        fd, temp_zip_path = tempfile.mkstemp(suffix=".zip")
        os.close(fd)

        photo_count = 0
        with zipfile.ZipFile(temp_zip_path, "w", zipfile.ZIP_STORED) as zf:
            for idx, photo in enumerate(photos, 1):
                if not photo.image:
                    continue

                original_name = photo.original_filename or f"photo_{photo.id}.jpg"
                base_filename = f"{idx:03d}_{original_name}"

                if _stream_file_to_zip(zf, photo.image, f"full_resolution/{base_filename}", photo.id):
                    photo_count += 1

                if photo.image_optimized:
                    _stream_file_to_zip(zf, photo.image_optimized, f"optimized/{base_filename}", photo.id)

        if album.zip_file:
            try:
                album.zip_file.delete(save=False)
            except Exception as e:
                logger.warning(f"Failed to delete old ZIP for album {album_id}: {e}")

        zip_size = os.path.getsize(temp_zip_path)
        zip_filename = f"{album.slug}_{timezone.now().strftime('%Y%m%d')}.zip"

        with open(temp_zip_path, "rb") as f:
            album.zip_file.save(zip_filename, File(f), save=False)

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

        logger.info(f"Generated ZIP for album {album_id}: {zip_filename} ({zip_size} bytes, {photo_count} photos)")

        return {
            "status": "success",
            "album_id": album_id,
            "filename": zip_filename,
            "size": zip_size,
            "photo_count": photo_count,
        }

    except Exception as e:
        logger.error(f"Failed to generate ZIP for album {album_id}: {e}", exc_info=True)
        album.zip_generation_status = "failed"
        album.save(update_fields=["zip_generation_status"])
        raise
    finally:
        if temp_zip_path and os.path.exists(temp_zip_path):
            os.unlink(temp_zip_path)
