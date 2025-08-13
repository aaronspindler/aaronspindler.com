"""
Optimized Django admin configuration for the photos app with performance improvements.
"""
import json
from django.contrib import admin
from django.utils.html import mark_safe
from django.urls import reverse, path
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Count, Prefetch
from django.contrib import messages
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import cache_page
from concurrent.futures import ThreadPoolExecutor
import logging

from .models import Album, Photo
from .cache import invalidate_album_cache, invalidate_photo_cache
from .image_processor import ImageProcessor
from .utils import generate_thumbnail, get_thumbnail_filename

logger = logging.getLogger(__name__)


class OptimizedPhotoInline(admin.TabularInline):
    """
    Optimized inline admin for photos within an album.
    """
    model = Photo
    extra = 0  # Don't show extra empty forms by default
    fields = ['title', 'caption', 'original_image', 'order', 'thumbnail_preview']
    readonly_fields = ['thumbnail_preview']
    ordering = ['order', '-created_at']
    show_change_link = True
    
    # Reduce queries with select/prefetch related
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('album').only(
            'id', 'album_id', 'title', 'caption', 
            'original_image', 'thumbnail', 'order', 'created_at'
        )
    
    def thumbnail_preview(self, obj):
        """Display thumbnail preview with lazy loading."""
        if obj.thumbnail:
            return mark_safe(
                f'<img data-src="{obj.thumbnail.url}" '
                f'class="lazy-thumbnail" width="50" height="50" '
                f'style="object-fit: cover;" loading="lazy" />'
            )
        elif obj.original_image:
            return mark_safe(
                f'<img data-src="{obj.original_image.url}" '
                f'class="lazy-thumbnail" width="50" height="50" '
                f'style="object-fit: cover;" loading="lazy" />'
            )
        return "No image"
    thumbnail_preview.short_description = 'Preview'


@admin.register(Album)
class OptimizedAlbumAdmin(admin.ModelAdmin):
    """
    Optimized admin configuration for Album model.
    """
    list_display = ['title', 'is_published', 'cached_photo_count', 'cover_preview', 
                   'created_at', 'order']
    list_filter = ['is_published', 'created_at', 'updated_at']
    search_fields = ['title', 'description']
    list_editable = ['is_published', 'order']
    ordering = ['order', '-created_at']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'cached_photo_count', 'cover_preview_large']
    inlines = [OptimizedPhotoInline]
    list_per_page = 25
    list_select_related = []  # Album has no ForeignKeys to select
    
    fieldsets = (
        ('Album Information', {
            'fields': ('title', 'description', 'cover_image', 'cover_preview_large')
        }),
        ('Publishing', {
            'fields': ('is_published', 'order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Performance', {
            'fields': ('cached_photo_count',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with annotations and prefetching."""
        qs = super().get_queryset(request)
        # Annotate with photo count to avoid N+1 queries
        qs = qs.annotate(
            photo_count_annotated=Count('photos')
        ).prefetch_related(
            Prefetch(
                'photos',
                queryset=Photo.objects.only('id', 'album_id')
            )
        )
        return qs
    
    def cached_photo_count(self, obj):
        """Display cached photo count with link."""
        # Use annotated count if available
        if hasattr(obj, 'photo_count_annotated'):
            count = obj.photo_count_annotated
        else:
            # Fallback to cached count
            cache_key = f'admin:album:{obj.id}:photo_count'
            count = cache.get(cache_key)
            if count is None:
                count = obj.photos.count()
                cache.set(cache_key, count, 300)  # Cache for 5 minutes
        
        url = reverse('admin:photos_photo_changelist') + f'?album__id__exact={obj.id}'
        return mark_safe(f'<a href="{url}">{count} photo(s)</a>')
    
    cached_photo_count.short_description = 'Photos'
    cached_photo_count.admin_order_field = 'photo_count_annotated'
    
    def cover_preview(self, obj):
        """Display small cover image preview with lazy loading."""
        if obj.cover_image:
            return mark_safe(
                f'<img data-src="{obj.cover_image.url}" '
                f'class="lazy-thumbnail" width="50" height="50" '
                f'style="object-fit: cover;" loading="lazy" />'
            )
        return "No cover"
    cover_preview.short_description = 'Cover'
    
    def cover_preview_large(self, obj):
        """Display larger cover image preview."""
        if obj.cover_image:
            return mark_safe(
                f'<img src="{obj.cover_image.url}" width="200" '
                f'style="max-height: 200px; object-fit: cover;" loading="lazy" />'
            )
        return "No cover image set"
    cover_preview_large.short_description = 'Current Cover'
    
    def get_urls(self):
        """Add custom admin URLs for batch operations."""
        urls = super().get_urls()
        custom_urls = [
            path('batch-operations/', self.admin_site.admin_view(self.batch_operations_view), 
                 name='photos_album_batch'),
            path('regenerate-all-thumbnails/', 
                 self.admin_site.admin_view(self.regenerate_all_thumbnails_view),
                 name='photos_regenerate_all_thumbnails'),
            path('warm-cache/', self.admin_site.admin_view(self.warm_cache_view),
                 name='photos_warm_cache'),
        ]
        return custom_urls + urls
    
    def batch_operations_view(self, request):
        """View for batch operations."""
        if request.method == 'POST':
            operation = request.POST.get('operation')
            album_ids = request.POST.getlist('album_ids[]')
            
            if operation == 'regenerate_thumbnails':
                return self._batch_regenerate_thumbnails(request, album_ids)
            elif operation == 'publish':
                return self._batch_publish(request, album_ids, True)
            elif operation == 'unpublish':
                return self._batch_publish(request, album_ids, False)
            elif operation == 'delete':
                return self._batch_delete(request, album_ids)
        
        return render(request, 'admin/photos/batch_operations.html')
    
    @transaction.atomic
    def _batch_regenerate_thumbnails(self, request, album_ids):
        """Regenerate thumbnails for selected albums."""
        total_processed = 0
        total_failed = 0
        
        albums = Album.objects.filter(id__in=album_ids).prefetch_related('photos')
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            for album in albums:
                for photo in album.photos.all():
                    if photo.original_image:
                        futures.append(
                            executor.submit(self._regenerate_single_thumbnail, photo)
                        )
            
            for future in futures:
                success = future.result()
                if success:
                    total_processed += 1
                else:
                    total_failed += 1
        
        # Invalidate cache
        for album_id in album_ids:
            invalidate_album_cache(album_id)
        
        messages.success(
            request,
            f'Regenerated {total_processed} thumbnails. {total_failed} failed.'
        )
        
        return JsonResponse({
            'status': 'success',
            'processed': total_processed,
            'failed': total_failed
        })
    
    def _regenerate_single_thumbnail(self, photo):
        """Regenerate thumbnail for a single photo."""
        try:
            processor = ImageProcessor(photo.original_image)
            thumbnail_content = processor.generate_thumbnail()
            
            if thumbnail_content:
                thumb_filename = get_thumbnail_filename(photo.original_image.name)
                photo.thumbnail.save(thumb_filename, thumbnail_content, save=True)
                return True
        except Exception as e:
            logger.error(f"Failed to regenerate thumbnail for photo {photo.id}: {e}")
        
        return False
    
    @transaction.atomic
    def _batch_publish(self, request, album_ids, publish=True):
        """Batch publish/unpublish albums."""
        count = Album.objects.filter(id__in=album_ids).update(is_published=publish)
        
        # Invalidate cache for affected albums
        for album_id in album_ids:
            invalidate_album_cache(album_id)
        
        action = 'published' if publish else 'unpublished'
        messages.success(request, f'{count} album(s) {action} successfully.')
        
        return JsonResponse({'status': 'success', 'count': count})
    
    @transaction.atomic
    def _batch_delete(self, request, album_ids):
        """Batch delete albums."""
        albums = Album.objects.filter(id__in=album_ids)
        count = albums.count()
        
        # Invalidate cache before deletion
        for album_id in album_ids:
            invalidate_album_cache(album_id)
        
        albums.delete()
        
        messages.success(request, f'{count} album(s) deleted successfully.')
        
        return JsonResponse({'status': 'success', 'count': count})
    
    def regenerate_all_thumbnails_view(self, request):
        """Regenerate all thumbnails in background."""
        from django.core.management import call_command
        
        # This would ideally be done with Celery or similar
        call_command('generate_thumbnails', '--force')
        
        messages.success(request, 'Thumbnail regeneration started in background.')
        return redirect('admin:photos_album_changelist')
    
    def warm_cache_view(self, request):
        """Warm the cache for all albums."""
        from django.core.management import call_command
        
        call_command('warm_cache')
        
        messages.success(request, 'Cache warming completed.')
        return redirect('admin:photos_album_changelist')
    
    actions = ['publish_albums', 'unpublish_albums', 'async_regenerate_thumbnails']
    
    def publish_albums(self, request, queryset):
        """Bulk action to publish selected albums."""
        count = queryset.update(is_published=True)
        
        # Invalidate cache
        for album in queryset:
            invalidate_album_cache(album.pk)
        
        self.message_user(request, f'{count} album(s) published successfully.')
    publish_albums.short_description = 'Publish selected albums'
    
    def unpublish_albums(self, request, queryset):
        """Bulk action to unpublish selected albums."""
        count = queryset.update(is_published=False)
        
        # Invalidate cache
        for album in queryset:
            invalidate_album_cache(album.pk)
        
        self.message_user(request, f'{count} album(s) unpublished successfully.')
    unpublish_albums.short_description = 'Unpublish selected albums'
    
    def async_regenerate_thumbnails(self, request, queryset):
        """Async thumbnail regeneration."""
        album_ids = list(queryset.values_list('id', flat=True))
        
        # Store task in cache for progress tracking
        task_id = f"thumbnail_regen_{request.user.id}_{id(queryset)}"
        cache.set(task_id, {
            'status': 'pending',
            'album_ids': album_ids,
            'total': len(album_ids),
            'processed': 0
        }, 3600)
        
        # Start async task (would use Celery in production)
        self._start_async_thumbnail_generation(task_id, album_ids)
        
        self.message_user(
            request,
            f'Thumbnail regeneration started for {len(album_ids)} albums. '
            f'Task ID: {task_id}'
        )
    async_regenerate_thumbnails.short_description = 'Regenerate thumbnails (async)'
    
    def _start_async_thumbnail_generation(self, task_id, album_ids):
        """Start async thumbnail generation task."""
        # In production, this would be a Celery task
        # For now, we'll use threading as a demonstration
        import threading
        
        def generate():
            task_data = cache.get(task_id)
            task_data['status'] = 'processing'
            cache.set(task_id, task_data, 3600)
            
            for i, album_id in enumerate(album_ids):
                album = Album.objects.prefetch_related('photos').get(pk=album_id)
                
                for photo in album.photos.all():
                    if photo.original_image:
                        self._regenerate_single_thumbnail(photo)
                
                task_data['processed'] = i + 1
                cache.set(task_id, task_data, 3600)
            
            task_data['status'] = 'completed'
            cache.set(task_id, task_data, 3600)
        
        thread = threading.Thread(target=generate)
        thread.daemon = True
        thread.start()


@admin.register(Photo)
class OptimizedPhotoAdmin(admin.ModelAdmin):
    """
    Optimized admin configuration for Photo model.
    """
    list_display = ['title_display', 'album_link', 'thumbnail_preview', 'order', 'created_at']
    list_filter = ['album', 'created_at']
    search_fields = ['title', 'caption', 'album__title']
    autocomplete_fields = ['album']
    list_editable = ['order']
    ordering = ['album', 'order', '-created_at']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'thumbnail_preview_large', 'original_preview_large',
                      'image_metadata']
    list_per_page = 50
    list_select_related = ['album']  # Optimize ForeignKey queries
    
    fieldsets = (
        ('Photo Information', {
            'fields': ('album', 'title', 'caption')
        }),
        ('Images', {
            'fields': ('original_image', 'original_preview_large', 
                      'thumbnail', 'thumbnail_preview_large')
        }),
        ('Metadata', {
            'fields': ('image_metadata',),
            'classes': ('collapse',)
        }),
        ('Ordering', {
            'fields': ('order',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('album').only(
            'id', 'album_id', 'title', 'caption', 
            'original_image', 'thumbnail', 'order', 'created_at',
            'album__title'  # Include album title for display
        )
    
    def title_display(self, obj):
        """Display title or fallback text."""
        return obj.title or f"Untitled (ID: {obj.id})"
    title_display.short_description = 'Title'
    title_display.admin_order_field = 'title'
    
    def album_link(self, obj):
        """Display album with link to album change page."""
        if obj.album:
            url = reverse('admin:photos_album_change', args=[obj.album.pk])
            return mark_safe(f'<a href="{url}">{obj.album.title}</a>')
        return "-"
    album_link.short_description = 'Album'
    album_link.admin_order_field = 'album__title'
    
    def thumbnail_preview(self, obj):
        """Display thumbnail preview with lazy loading."""
        if obj.thumbnail:
            return mark_safe(
                f'<img data-src="{obj.thumbnail.url}" '
                f'class="lazy-thumbnail" width="50" height="50" '
                f'style="object-fit: cover;" loading="lazy" />'
            )
        elif obj.original_image:
            return mark_safe(
                f'<img data-src="{obj.original_image.url}" '
                f'class="lazy-thumbnail" width="50" height="50" '
                f'style="object-fit: cover;" loading="lazy" />'
            )
        return "No thumbnail"
    thumbnail_preview.short_description = 'Preview'
    
    def thumbnail_preview_large(self, obj):
        """Display larger thumbnail preview."""
        if obj.thumbnail:
            return mark_safe(
                f'<img src="{obj.thumbnail.url}" width="200" '
                f'style="max-height: 200px; object-fit: cover;" loading="lazy" />'
            )
        return "No thumbnail generated"
    thumbnail_preview_large.short_description = 'Thumbnail Preview'
    
    def original_preview_large(self, obj):
        """Display original image preview."""
        if obj.original_image:
            return mark_safe(
                f'<img src="{obj.original_image.url}" width="400" '
                f'style="max-height: 400px; object-fit: contain;" loading="lazy" />'
                f'<br><small>Full size: <a href="{obj.original_image.url}" '
                f'target="_blank">{obj.original_image.url}</a></small>'
            )
        return "No image"
    original_preview_large.short_description = 'Original Image Preview'
    
    def image_metadata(self, obj):
        """Display image metadata."""
        if obj.original_image:
            try:
                from photos.storage_optimized import OptimizedS3Storage
                storage = OptimizedS3Storage()
                metadata = storage.get_object_metadata(obj.original_image.name)
                
                if metadata:
                    return mark_safe(
                        f"<pre>{json.dumps(metadata, indent=2)}</pre>"
                    )
            except Exception as e:
                logger.error(f"Error getting metadata: {e}")
        
        return "No metadata available"
    image_metadata.short_description = 'Image Metadata'
    
    actions = ['regenerate_thumbnails', 'optimize_images', 'bulk_move_album']
    
    def regenerate_thumbnails(self, request, queryset):
        """Bulk action to regenerate thumbnails."""
        processed = 0
        failed = 0
        
        for photo in queryset.select_related('album'):
            if photo.original_image:
                if self._regenerate_single_thumbnail(photo):
                    processed += 1
                else:
                    failed += 1
            
            # Invalidate photo cache
            invalidate_photo_cache(photo.pk, photo.album_id)
        
        self.message_user(request, f'Regenerated {processed} thumbnail(s). {failed} failed.')
    regenerate_thumbnails.short_description = 'Regenerate thumbnails'
    
    def optimize_images(self, request, queryset):
        """Optimize selected images."""
        from photos.image_processor import ImageProcessor
        
        optimized = 0
        for photo in queryset:
            try:
                processor = ImageProcessor(photo.original_image)
                optimized_content = processor.optimize_image()
                
                # Save optimized version
                photo.original_image.save(
                    photo.original_image.name,
                    optimized_content,
                    save=True
                )
                optimized += 1
                
            except Exception as e:
                logger.error(f"Failed to optimize photo {photo.id}: {e}")
        
        self.message_user(request, f'Optimized {optimized} image(s).')
    optimize_images.short_description = 'Optimize selected images'
    
    def bulk_move_album(self, request, queryset):
        """Move photos to a different album."""
        # This would show an intermediate page to select target album
        selected = queryset.values_list('pk', flat=True)
        request.session['selected_photos'] = list(selected)
        
        return redirect('admin:photos_photo_move')
    bulk_move_album.short_description = 'Move to different album'
    
    def _regenerate_single_thumbnail(self, photo):
        """Helper to regenerate a single thumbnail."""
        try:
            from photos.image_processor import ImageProcessor
            
            processor = ImageProcessor(photo.original_image)
            thumbnail_content = processor.generate_thumbnail()
            
            if thumbnail_content:
                thumb_filename = get_thumbnail_filename(photo.original_image.name)
                photo.thumbnail.save(thumb_filename, thumbnail_content, save=True)
                return True
        except Exception as e:
            logger.error(f"Failed to regenerate thumbnail for photo {photo.id}: {e}")
        
        return False


# Add custom CSS and JavaScript for lazy loading
class PhotosAdminSite(admin.AdminSite):
    """Custom admin site with performance optimizations."""
    
    def each_context(self, request):
        context = super().each_context(request)
        
        # Add custom CSS/JS for lazy loading
        context['extra_head'] = mark_safe("""
        <style>
            .lazy-thumbnail {
                background: #f0f0f0;
                min-height: 50px;
            }
        </style>
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                // Lazy load images
                const lazyImages = document.querySelectorAll('.lazy-thumbnail');
                const imageObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            img.src = img.dataset.src;
                            img.classList.remove('lazy-thumbnail');
                            observer.unobserve(img);
                        }
                    });
                });
                
                lazyImages.forEach(img => imageObserver.observe(img));
            });
        </script>
        """)
        
        return context


# Customize admin site header and title
admin.site.site_header = "Optimized Photo Gallery Admin"
admin.site.site_title = "Photo Gallery Admin"
admin.site.index_title = "Photo Gallery Management"