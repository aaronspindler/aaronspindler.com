"""
Management command to optimize existing images in the gallery.
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from photos.models import Album, Photo
from photos.image_processor import ImageProcessor, RESPONSIVE_SIZES
from photos.storage_optimized import OptimizedS3Storage
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Optimize existing images with WebP conversion and responsive sizes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--album-id',
            type=int,
            help='Specific album ID to optimize'
        )
        parser.add_argument(
            '--photo-id',
            type=int,
            help='Specific photo ID to optimize'
        )
        parser.add_argument(
            '--generate-webp',
            action='store_true',
            default=True,
            help='Generate WebP versions'
        )
        parser.add_argument(
            '--generate-responsive',
            action='store_true',
            help='Generate all responsive image sizes'
        )
        parser.add_argument(
            '--optimize-storage',
            action='store_true',
            help='Optimize S3 storage class based on access patterns'
        )
        parser.add_argument(
            '--parallel',
            type=int,
            default=4,
            help='Number of parallel workers'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
    
    def handle(self, *args, **options):
        album_id = options.get('album_id')
        photo_id = options.get('photo_id')
        generate_webp = options.get('generate_webp')
        generate_responsive = options.get('generate_responsive')
        optimize_storage = options.get('optimize_storage')
        parallel = options.get('parallel')
        dry_run = options.get('dry_run')
        
        try:
            if photo_id:
                self._optimize_single_photo(photo_id, generate_webp, generate_responsive, 
                                           optimize_storage, dry_run)
            elif album_id:
                self._optimize_album(album_id, generate_webp, generate_responsive, 
                                    optimize_storage, parallel, dry_run)
            else:
                self._optimize_all(generate_webp, generate_responsive, optimize_storage, 
                                  parallel, dry_run)
                
        except Exception as e:
            logger.error(f"Image optimization failed: {str(e)}")
            raise CommandError(f"Image optimization failed: {str(e)}")
    
    def _optimize_single_photo(self, photo_id, generate_webp=True, generate_responsive=False,
                              optimize_storage=False, dry_run=False):
        """Optimize a single photo."""
        try:
            photo = Photo.objects.select_related('album').get(pk=photo_id)
            
            if dry_run:
                self.stdout.write(f'Would optimize photo {photo_id}: {photo}')
                return
            
            result = self._process_photo(photo, generate_webp, generate_responsive, optimize_storage)
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully optimized photo {photo_id}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to optimize photo {photo_id}: {result.get("error")}')
                )
                
        except Photo.DoesNotExist:
            raise CommandError(f'Photo with ID {photo_id} does not exist')
    
    def _optimize_album(self, album_id, generate_webp=True, generate_responsive=False,
                       optimize_storage=False, parallel=4, dry_run=False):
        """Optimize all photos in an album."""
        try:
            album = Album.objects.prefetch_related('photos').get(pk=album_id)
            photos = album.photos.all()
            
            self.stdout.write(f'Optimizing {photos.count()} photos in album "{album.title}"')
            
            if dry_run:
                for photo in photos:
                    self.stdout.write(f'Would optimize: {photo}')
                return
            
            results = self._process_photos_parallel(photos, generate_webp, generate_responsive,
                                                   optimize_storage, parallel)
            
            successful = sum(1 for r in results if r['success'])
            failed = len(results) - successful
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Album optimization complete: {successful} successful, {failed} failed'
                )
            )
            
        except Album.DoesNotExist:
            raise CommandError(f'Album with ID {album_id} does not exist')
    
    def _optimize_all(self, generate_webp=True, generate_responsive=False,
                     optimize_storage=False, parallel=4, dry_run=False):
        """Optimize all photos in the database."""
        photos = Photo.objects.select_related('album').all()
        total = photos.count()
        
        self.stdout.write(f'Optimizing {total} photos...')
        
        if dry_run:
            self.stdout.write('DRY RUN - no changes will be made')
            for photo in photos[:10]:  # Show first 10 as example
                self.stdout.write(f'Would optimize: {photo}')
            if total > 10:
                self.stdout.write(f'... and {total - 10} more')
            return
        
        results = self._process_photos_parallel(photos, generate_webp, generate_responsive,
                                               optimize_storage, parallel)
        
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Optimization complete: {successful} successful, {failed} failed'
            )
        )
    
    def _process_photos_parallel(self, photos, generate_webp, generate_responsive,
                                optimize_storage, max_workers):
        """Process multiple photos in parallel."""
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._process_photo, photo, generate_webp, 
                    generate_responsive, optimize_storage
                ): photo 
                for photo in photos
            }
            
            for future in as_completed(futures):
                photo = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['success']:
                        self.stdout.write(f'✓ Optimized {photo}')
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'✗ Failed {photo}: {result.get("error")}')
                        )
                        
                except Exception as e:
                    results.append({'success': False, 'error': str(e)})
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error processing {photo}: {str(e)}')
                    )
        
        return results
    
    def _process_photo(self, photo, generate_webp=True, generate_responsive=False,
                      optimize_storage=False):
        """Process a single photo with optimizations."""
        result = {'success': False, 'photo_id': photo.pk}
        
        try:
            processor = ImageProcessor(photo.original_image)
            storage = OptimizedS3Storage()
            
            # Generate WebP version
            if generate_webp:
                webp_content = processor.generate_webp()
                webp_path = f"photos/webp/{photo.album.pk}/{photo.pk}.webp"
                storage.save(webp_path, webp_content)
                result['webp_generated'] = True
                logger.info(f"Generated WebP for photo {photo.pk}")
            
            # Generate responsive sizes
            if generate_responsive:
                responsive_images = processor.generate_responsive_images(['jpeg', 'webp'])
                
                for size_name, formats in responsive_images.items():
                    for format_name, content in formats.items():
                        path = f"photos/responsive/{photo.album.pk}/{photo.pk}_{size_name}.{format_name}"
                        storage.save(path, content)
                
                result['responsive_generated'] = True
                logger.info(f"Generated responsive images for photo {photo.pk}")
            
            # Optimize storage class
            if optimize_storage:
                # Original images can be moved to infrequent access
                storage.optimize_storage_class(
                    photo.original_image.name, 
                    access_pattern='infrequent'
                )
                
                # Thumbnails stay in standard storage
                if photo.thumbnail:
                    storage.optimize_storage_class(
                        photo.thumbnail.name,
                        access_pattern='frequent'
                    )
                
                result['storage_optimized'] = True
                logger.info(f"Optimized storage for photo {photo.pk}")
            
            # Generate blur placeholder
            placeholder = processor.generate_blur_placeholder()
            
            # Store placeholder in database (you might want to add a field for this)
            # photo.blur_placeholder = placeholder
            # photo.save(update_fields=['blur_placeholder'])
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Failed to process photo {photo.pk}: {str(e)}")
        
        return result