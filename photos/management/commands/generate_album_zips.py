from django.core.management.base import BaseCommand

from photos.models import PhotoAlbum
from photos.tasks import generate_album_zip, regenerate_all_album_zips


class Command(BaseCommand):
    help = "Generate zip files for photo albums"

    def add_arguments(self, parser):
        parser.add_argument("--album-id", type=int, help="Generate zip for a specific album ID")
        parser.add_argument("--album-slug", type=str, help="Generate zip for a specific album by slug")
        parser.add_argument(
            "--all",
            action="store_true",
            help="Regenerate zips for all albums that allow downloads",
        )
        parser.add_argument(
            "--async",
            action="store_true",
            dest="use_async",
            help="Use Celery to process asynchronously",
        )

    def handle(self, *args, **options):
        use_async = options.get("use_async", False)

        if options.get("all"):
            self.stdout.write("Regenerating zips for all albums with downloads enabled...")

            if use_async:
                __result = regenerate_all_album_zips.delay()
                self.stdout.write(self.style.SUCCESS("Triggered async regeneration of all album zips"))
            else:
                albums = PhotoAlbum.objects.filter(allow_downloads=True)
                for album in albums:
                    self.stdout.write(f"Processing album: {album.title}")
                    result = generate_album_zip(album.pk)
                    if result:
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Successfully generated zips for {album.title}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"  ✗ Failed to generate zips for {album.title}"))

        elif options.get("album_id"):
            album_id = options["album_id"]
            try:
                album = PhotoAlbum.objects.get(pk=album_id)
                self.stdout.write(f"Generating zip for album: {album.title}")

                if use_async:
                    generate_album_zip.delay(album_id)
                    self.stdout.write(self.style.SUCCESS(f"Triggered async zip generation for {album.title}"))
                else:
                    result = generate_album_zip(album_id)
                    if result:
                        self.stdout.write(self.style.SUCCESS(f"Successfully generated zips for {album.title}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"Failed to generate zips for {album.title}"))

            except PhotoAlbum.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Album with ID {album_id} does not exist"))

        elif options.get("album_slug"):
            slug = options["album_slug"]
            try:
                album = PhotoAlbum.objects.get(slug=slug)
                self.stdout.write(f"Generating zip for album: {album.title}")

                if use_async:
                    generate_album_zip.delay(album.pk)
                    self.stdout.write(self.style.SUCCESS(f"Triggered async zip generation for {album.title}"))
                else:
                    result = generate_album_zip(album.pk)
                    if result:
                        self.stdout.write(self.style.SUCCESS(f"Successfully generated zips for {album.title}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"Failed to generate zips for {album.title}"))

            except PhotoAlbum.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Album with slug "{slug}" does not exist'))

        else:
            self.stdout.write(self.style.WARNING("Please specify --album-id, --album-slug, or --all"))
