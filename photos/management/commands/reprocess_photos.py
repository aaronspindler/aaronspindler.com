"""
Management command to reprocess photos locally without Celery.

Usage:
    python manage.py reprocess_photos
    python manage.py reprocess_photos --status pending
    python manage.py reprocess_photos --ids 1,2,3
    python manage.py reprocess_photos --limit 10
"""

import logging

from django.core.management.base import BaseCommand

from photos.models import Photo

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reprocess photos locally (extract metadata, create optimized versions)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--status",
            type=str,
            choices=["pending", "processing", "complete", "failed"],
            help="Only process photos with this status",
        )
        parser.add_argument(
            "--ids",
            type=str,
            help="Comma-separated list of photo IDs to process (e.g., '1,2,3')",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of photos to process",
        )

    def handle(self, *args, **options):
        status = options["status"]
        ids_str = options["ids"]
        limit = options["limit"]

        photos = Photo.objects.all()

        if ids_str:
            photo_ids = [int(id.strip()) for id in ids_str.split(",")]
            photos = photos.filter(id__in=photo_ids)
            self.stdout.write(f"Filtering to {len(photo_ids)} specific photo(s)")
        elif status:
            photos = photos.filter(processing_status=status)
            self.stdout.write(f"Filtering to photos with status: {status}")

        if limit:
            photos = photos[:limit]
            self.stdout.write(f"Limiting to {limit} photo(s)")

        total = photos.count()

        if total == 0:
            self.stdout.write(self.style.WARNING("No photos to process"))
            return

        self.stdout.write(self.style.SUCCESS(f"\nStarting local photo processing for {total} photo(s)...\n"))

        success_count = 0
        error_count = 0
        skipped_count = 0

        for idx, photo in enumerate(photos, 1):
            photo_id = photo.id
            photo_name = str(photo)

            try:
                if not photo.image:
                    self.stdout.write(
                        self.style.WARNING(f"[{idx}/{total}] Skipping {photo_name} (ID: {photo_id}) - No image file")
                    )
                    skipped_count += 1
                    continue

                self.stdout.write(f"[{idx}/{total}] Processing {photo_name} (ID: {photo_id})...")

                photo.process_image_async()

                self.stdout.write(
                    self.style.SUCCESS(f"[{idx}/{total}] ✓ Successfully processed {photo_name} (ID: {photo_id})")
                )
                success_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"[{idx}/{total}] ✗ Failed to process {photo_name} (ID: {photo_id}): {str(e)}")
                )
                logger.exception(f"Error processing photo {photo_id}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'=' * 60}\n"
                f"Photo Processing Complete!\n"
                f"{'=' * 60}\n"
                f"Total:     {total}\n"
                f"Success:   {success_count}\n"
                f"Skipped:   {skipped_count}\n"
                f"Failed:    {error_count}\n"
                f"{'=' * 60}\n"
            )
        )

        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f"\n⚠ {error_count} photo(s) failed to process. Check logs for details.")
            )
