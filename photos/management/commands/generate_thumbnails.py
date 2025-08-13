"""
Management command to generate or regenerate thumbnails for photos.
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from photos.models import Album, Photo
from photos.utils import generate_thumbnail, get_thumbnail_filename
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate or regenerate thumbnails for photos'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--album-id',
            type=int,
            help='Specific album ID to generate thumbnails for'
        )
        parser.add_argument(
            '--photo-id',
            type=int,
            help='Specific photo ID to generate thumbnail for'
        )
        parser.add_argument(
            '--missing-only',
            action='store_true',
            help='Only generate thumbnails for photos without them'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration even if thumbnail exists'
        )
        parser.add_argument(
            '--size',
            type=str,
            default='400x400',
            help='Thumbnail size (e.g., 400x400)'
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=85,
            help='JPEG quality (1-100)'
        )
        parser.add_argument(
            '--parallel',
            type=int,
            default=4,
            help='Number of parallel workers'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Process photos in batches of this size'
        )
    
    def handle(self, *args, **options):
        album_id = options.get('album_id')
        photo_id = options.get('photo_id')
        missing_only = options.get('missing_only')
        force = options.get('force')
        size = options.get('size')
        quality = options.get('quality')
        parallel = options.get('parallel')
        batch_size = options.get('batch_size')
        
        # Parse size
        try:
            width, height = map(int, size.split('x'))
            thumbnail_size = (width, height)
        except ValueError:
            raise CommandError(f'Invalid size format: {size}. Use WIDTHxHEIGHT (e.g., 400x400)')
        
        try:
            if photo_id:
                self._generate_single(photo_id, thumbnail_size, quality, force)
            elif album_id:
                self._generate_album(album_id, thumbnail_size, quality, missing_only, 
                                   force, parallel, batch_size)
            else:
                self._generate_all(thumbnail_size, quality, missing_only, force, 
                                 parallel, batch_size)
                
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {str(e)}")
            raise CommandError(f"Thumbnail generation failed: {str(e)}")
    
    def _generate_single(self, photo_id, size, quality, force=False):
        """Generate thumbnail for a single photo."""
        try:
            photo = Photo.objects.get(pk=photo_id)
            
            if photo.thumbnail and not force:
                self.stdout.write(
                    self.style.WARNING(f'Photo {photo_id} already has thumbnail. Use --force to regenerate.')
                )
                return
            
            success = self._process_photo(photo, size, quality)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully generated thumbnail for photo {photo_id}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to generate thumbnail for photo {photo_id}')
                )
                
        except Photo.DoesNotExist:
            raise CommandError(f'Photo with ID {photo_id} does not exist')
    
    def _generate_album(self, album_id, size, quality, missing_only=False, force=False,
                       parallel=4, batch_size=100):
        """Generate thumbnails for all photos in an album."""
        try:
            album = Album.objects.prefetch_related('photos').get(pk=album_id)
            photos = album.photos.all()
            
            if missing_only:
                photos = photos.filter(thumbnail='')
            
            total = photos.count()
            self.stdout.write(f'Generating thumbnails for {total} photos in album "{album.title}"')
            
            if total == 0:
                self.stdout.write('No photos to process')
                return
            
            results = self._process_batch(photos, size, quality, force, parallel, batch_size)
            
            successful = sum(1 for r in results if r)
            failed = len(results) - successful
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Thumbnail generation complete: {successful} successful, {failed} failed'
                )
            )
            
        except Album.DoesNotExist:
            raise CommandError(f'Album with ID {album_id} does not exist')
    
    def _generate_all(self, size, quality, missing_only=False, force=False,
                     parallel=4, batch_size=100):
        """Generate thumbnails for all photos."""
        photos = Photo.objects.select_related('album').all()
        
        if missing_only:
            photos = photos.filter(thumbnail='')
        
        total = photos.count()
        self.stdout.write(f'Generating thumbnails for {total} photos...')
        
        if total == 0:
            self.stdout.write('No photos to process')
            return
        
        results = self._process_batch(photos, size, quality, force, parallel, batch_size)
        
        successful = sum(1 for r in results if r)
        failed = len(results) - successful
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Thumbnail generation complete: {successful} successful, {failed} failed'
            )
        )
        
        # Print statistics
        self._print_statistics(successful, failed)
    
    def _process_batch(self, photos, size, quality, force, max_workers, batch_size):
        """Process photos in batches with parallel execution."""
        results = []
        processed = 0
        total = photos.count()
        
        # Process in batches to avoid memory issues
        for batch_start in range(0, total, batch_size):
            batch = photos[batch_start:batch_start + batch_size]
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._process_photo, photo, size, quality, force): photo
                    for photo in batch
                }
                
                for future in as_completed(futures):
                    photo = futures[future]
                    try:
                        success = future.result()
                        results.append(success)
                        processed += 1
                        
                        if success:
                            self.stdout.write(f'✓ Generated thumbnail for {photo} ({processed}/{total})')
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'✗ Skipped {photo} ({processed}/{total})')
                            )
                            
                    except Exception as e:
                        results.append(False)
                        processed += 1
                        self.stdout.write(
                            self.style.ERROR(f'✗ Error processing {photo}: {str(e)} ({processed}/{total})')
                        )
                        logger.error(f"Error processing photo {photo.pk}: {str(e)}", exc_info=True)
        
        return results
    
    def _process_photo(self, photo, size, quality, force=False):
        """Process a single photo to generate thumbnail."""
        try:
            # Skip if thumbnail exists and not forcing
            if photo.thumbnail and not force:
                logger.debug(f"Skipping photo {photo.pk} - thumbnail exists")
                return False
            
            # Generate thumbnail
            if not photo.original_image:
                logger.warning(f"Photo {photo.pk} has no original image")
                return False
            
            # Import here to avoid circular imports
            from photos.image_processor import ImageProcessor
            
            processor = ImageProcessor(photo.original_image)
            thumbnail_content = processor.generate_thumbnail(size=size)
            
            if thumbnail_content:
                # Save thumbnail
                thumb_filename = get_thumbnail_filename(photo.original_image.name)
                
                # Delete old thumbnail if it exists
                if photo.thumbnail:
                    try:
                        photo.thumbnail.delete(save=False)
                    except Exception as e:
                        logger.warning(f"Could not delete old thumbnail: {e}")
                
                # Save new thumbnail
                photo.thumbnail.save(thumb_filename, thumbnail_content, save=True)
                
                logger.info(f"Generated thumbnail for photo {photo.pk}")
                return True
            else:
                logger.error(f"Failed to generate thumbnail for photo {photo.pk}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing photo {photo.pk}: {str(e)}", exc_info=True)
            return False
    
    def _print_statistics(self, successful, failed):
        """Print generation statistics."""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('THUMBNAIL GENERATION STATISTICS')
        self.stdout.write('='*50)
        self.stdout.write(f'Total processed: {successful + failed}')
        self.stdout.write(f'Successful: {successful}')
        self.stdout.write(f'Failed: {failed}')
        
        if successful > 0:
            success_rate = (successful / (successful + failed)) * 100
            self.stdout.write(f'Success rate: {success_rate:.1f}%')
        
        # Calculate approximate storage saved
        estimated_savings = successful * 0.3  # Assume thumbnails are 30% of original size
        self.stdout.write(f'Estimated bandwidth savings: ~{estimated_savings:.0f} MB')
        self.stdout.write('='*50)