"""
Management command to extract EXIF data from existing photos.
This is useful for backfilling EXIF data for photos that were uploaded
before the EXIF extraction feature was implemented.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from pages.models import Photo
from pages.image_utils import ExifExtractor
import json


class Command(BaseCommand):
    help = 'Extract and store EXIF data from existing photos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--photo-id',
            type=int,
            help='Process a specific photo by ID',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing EXIF data',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without saving changes to database',
        )

    def handle(self, *args, **options):
        photo_id = options.get('photo_id')
        overwrite = options.get('overwrite', False)
        dry_run = options.get('dry_run', False)
        
        if photo_id:
            try:
                photos = Photo.objects.filter(id=photo_id)
                if not photos.exists():
                    self.stdout.write(
                        self.style.ERROR(f'Photo with ID {photo_id} not found')
                    )
                    return
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error fetching photo: {e}')
                )
                return
        else:
            # Get all photos, optionally filtering those without EXIF data
            if not overwrite:
                photos = Photo.objects.filter(exif_data__isnull=True)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Found {photos.count()} photos without EXIF data'
                    )
                )
            else:
                photos = Photo.objects.all()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Processing all {photos.count()} photos'
                    )
                )
        
        if photos.count() == 0:
            self.stdout.write(
                self.style.WARNING('No photos to process')
            )
            return
        
        processed = 0
        errors = 0
        skipped = 0
        
        for photo in photos:
            try:
                # Skip if EXIF data exists and not overwriting
                if photo.exif_data and not overwrite:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping photo {photo.id} "{photo.title}" - EXIF data already exists'
                        )
                    )
                    continue
                
                self.stdout.write(
                    f'Processing photo {photo.id}: "{photo.title}"...'
                )
                
                # Extract EXIF data
                if photo.image:
                    photo.image.open()  # Ensure file is open
                    exif_data = ExifExtractor.extract_exif(photo.image)
                    
                    if exif_data:
                        # Process the extracted data
                        full_exif = exif_data.pop('full_exif', {})
                        
                        # Convert full EXIF data to JSON-serializable format
                        serializable_exif = {}
                        for key, value in full_exif.items():
                            try:
                                json.dumps(value)
                                serializable_exif[key] = value
                            except (TypeError, ValueError):
                                serializable_exif[key] = str(value)
                        
                        if not dry_run:
                            with transaction.atomic():
                                # Update the photo with EXIF data
                                photo.exif_data = serializable_exif
                                photo.camera_make = exif_data.get('camera_make', '')
                                photo.camera_model = exif_data.get('camera_model', '')
                                photo.lens_model = exif_data.get('lens_model', '')
                                photo.focal_length = exif_data.get('focal_length', '')
                                photo.aperture = exif_data.get('aperture', '')
                                photo.shutter_speed = exif_data.get('shutter_speed', '')
                                photo.iso = exif_data.get('iso')
                                photo.date_taken = exif_data.get('date_taken')
                                photo.gps_latitude = exif_data.get('gps_latitude')
                                photo.gps_longitude = exif_data.get('gps_longitude')
                                photo.gps_altitude = exif_data.get('gps_altitude')
                                
                                photo.save(update_fields=[
                                    'exif_data', 'camera_make', 'camera_model', 
                                    'lens_model', 'focal_length', 'aperture',
                                    'shutter_speed', 'iso', 'date_taken',
                                    'gps_latitude', 'gps_longitude', 'gps_altitude'
                                ])
                        
                        # Display extracted information
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Extracted EXIF data:')
                        )
                        if exif_data.get('camera_make'):
                            self.stdout.write(
                                f'    Camera: {exif_data.get("camera_make")} {exif_data.get("camera_model", "")}'
                            )
                        if exif_data.get('lens_model'):
                            self.stdout.write(f'    Lens: {exif_data.get("lens_model")}')
                        if exif_data.get('focal_length'):
                            self.stdout.write(f'    Focal Length: {exif_data.get("focal_length")}')
                        if exif_data.get('aperture'):
                            self.stdout.write(f'    Aperture: {exif_data.get("aperture")}')
                        if exif_data.get('shutter_speed'):
                            self.stdout.write(f'    Shutter Speed: {exif_data.get("shutter_speed")}')
                        if exif_data.get('iso'):
                            self.stdout.write(f'    ISO: {exif_data.get("iso")}')
                        if exif_data.get('date_taken'):
                            self.stdout.write(f'    Date Taken: {exif_data.get("date_taken")}')
                        if exif_data.get('gps_latitude') and exif_data.get('gps_longitude'):
                            self.stdout.write(
                                f'    GPS: {exif_data.get("gps_latitude")}, {exif_data.get("gps_longitude")}'
                            )
                        
                        processed += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠ No EXIF data found')
                        )
                        skipped += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠ No image file found')
                    )
                    skipped += 1
                    
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error processing photo {photo.id}: {e}')
                )
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Summary:'))
        self.stdout.write(self.style.SUCCESS(f'  Processed: {processed} photos'))
        self.stdout.write(self.style.WARNING(f'  Skipped: {skipped} photos'))
        self.stdout.write(self.style.ERROR(f'  Errors: {errors} photos'))
        
        if dry_run:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING('DRY RUN - No changes were saved to the database')
            )

