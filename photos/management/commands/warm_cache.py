"""
Management command to warm the cache for photo galleries.
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Prefetch
from photos.models import Album, Photo
from photos.cache import warm_album_cache, cache_album_photos, cache_album_count

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Warm the cache for photo galleries'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--album-id',
            type=int,
            help='Specific album ID to warm cache for'
        )
        parser.add_argument(
            '--published-only',
            action='store_true',
            default=True,
            help='Only warm cache for published albums'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cache refresh even if already cached'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of albums to process at once'
        )
    
    def handle(self, *args, **options):
        album_id = options.get('album_id')
        published_only = options.get('published_only')
        force = options.get('force')
        batch_size = options.get('batch_size')
        
        try:
            if album_id:
                # Warm cache for specific album
                self._warm_single_album(album_id, force)
            else:
                # Warm cache for all albums
                self._warm_all_albums(published_only, force, batch_size)
                
        except Exception as e:
            logger.error(f"Cache warming failed: {str(e)}")
            raise CommandError(f"Cache warming failed: {str(e)}")
    
    def _warm_single_album(self, album_id, force=False):
        """Warm cache for a single album."""
        try:
            album = Album.objects.prefetch_related('photos').get(pk=album_id)
            
            if force:
                from photos.cache import invalidate_album_cache
                invalidate_album_cache(album_id)
            
            warm_album_cache(album_id)
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully warmed cache for album {album_id} - {album.title}')
            )
            
        except Album.DoesNotExist:
            raise CommandError(f'Album with ID {album_id} does not exist')
    
    def _warm_all_albums(self, published_only=True, force=False, batch_size=10):
        """Warm cache for all albums."""
        queryset = Album.objects.all()
        
        if published_only:
            queryset = queryset.filter(is_published=True)
        
        queryset = queryset.prefetch_related(
            Prefetch('photos', queryset=Photo.objects.order_by('order', '-created_at'))
        )
        
        total_albums = queryset.count()
        processed = 0
        failed = 0
        
        self.stdout.write(f'Warming cache for {total_albums} albums...')
        
        # Process in batches
        for album in queryset.iterator(chunk_size=batch_size):
            try:
                if force:
                    from photos.cache import invalidate_album_cache
                    invalidate_album_cache(album.pk)
                
                # Warm various caches
                warm_album_cache(album.pk)
                cache_album_photos(album.pk)
                cache_album_count(album.pk)
                
                processed += 1
                
                if processed % 10 == 0:
                    self.stdout.write(f'Processed {processed}/{total_albums} albums...')
                    
            except Exception as e:
                failed += 1
                logger.error(f"Failed to warm cache for album {album.pk}: {str(e)}")
                self.stdout.write(
                    self.style.WARNING(f'Failed to warm cache for album {album.pk}: {str(e)}')
                )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Cache warming complete: {processed} successful, {failed} failed'
            )
        )
        
        # Warm album list cache
        from django.core.cache import cache
        from photos.views_optimized import OptimizedAlbumListView
        
        view = OptimizedAlbumListView()
        albums = view.get_queryset()
        cache.set('photos:album:list', list(albums[:50]), 60 * 30)  # Cache first 50 albums
        
        self.stdout.write(self.style.SUCCESS('Album list cache warmed'))