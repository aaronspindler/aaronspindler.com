import logging
import os
import tempfile
import zipfile

from django.core.files.base import ContentFile

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def generate_album_zip(album_id):
    """
    Generate a zip file containing all photos in an album.
    Creates zip files with different quality versions.
    """
    from photos.models import PhotoAlbum

    try:
        album = PhotoAlbum.objects.get(pk=album_id)

        if not album.allow_downloads:
            logger.info(f"Downloads not allowed for album {album.title}, skipping zip generation")
            return False

        photos = album.photos.all()

        if not photos.exists():
            logger.warning(f"No photos found in album {album.title}")
            if album.zip_file:
                album.zip_file.delete()
                album.zip_file = None
            if album.zip_file_optimized:
                album.zip_file_optimized.delete()
                album.zip_file_optimized = None
            album.save()
            return False

        zip_configs = [
            ("original", "zip_file", "original"),
            ("optimized", "zip_file_optimized", "optimized"),
        ]

        for zip_type, field_name, image_size in zip_configs:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
                tmp_path = tmp_file.name

                try:
                    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for index, photo in enumerate(photos, 1):
                            if image_size == "original":
                                image_field = photo.image
                            else:
                                image_field = photo.image_optimized or photo.image

                            if image_field:
                                try:
                                    image_field.open()
                                    image_data = image_field.read()

                                    ext = os.path.splitext(photo.original_filename or f"photo_{photo.pk}.jpg")[1]
                                    if photo.title:
                                        filename = f"{index:03d}_{photo.title}{ext}"
                                    else:
                                        filename = f"{index:03d}_{photo.original_filename or f'photo_{photo.pk}{ext}'}"

                                    filename = "".join(c for c in filename if c.isalnum() or c in ("_", "-", ".", " "))
                                    zip_file.writestr(filename, image_data)

                                except Exception as e:
                                    logger.error(f"Error adding photo {photo.pk} to zip: {e}")
                                finally:
                                    image_field.close()

                    with open(tmp_path, "rb") as f:
                        zip_content = ContentFile(f.read())
                        zip_filename = f"{album.slug}_{zip_type}_{album.photos.count()}_photos.zip"

                        old_field = getattr(album, field_name)
                        if old_field:
                            old_field.delete(save=False)

                        getattr(album, field_name).save(zip_filename, zip_content, save=False)

                    logger.info(f"Successfully generated {zip_type} zip for album {album.title}")

                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

        album.save()

        logger.info(f"Successfully generated all zip files for album {album.title}")
        return True

    except PhotoAlbum.DoesNotExist:
        logger.error(f"Album with id {album_id} does not exist")
        return False
    except Exception as e:
        logger.error(f"Error generating zip for album {album_id}: {e}")
        return False


@shared_task
def regenerate_all_album_zips():
    """
    Regenerate zip files for all albums that allow downloads.
    Useful for maintenance or after bulk changes.
    """
    from photos.models import PhotoAlbum

    albums = PhotoAlbum.objects.filter(allow_downloads=True)
    success_count = 0

    for album in albums:
        result = generate_album_zip.delay(album.pk)
        if result:
            success_count += 1

    logger.info(f"Triggered zip regeneration for {success_count} albums")
    return success_count
