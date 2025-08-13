"""
Django admin configuration for the photos app.
"""
from django.contrib import admin
from django.utils.html import mark_safe
from django.urls import reverse
from django.utils.safestring import SafeString
from .models import Album, Photo


class PhotoInline(admin.TabularInline):
    """
    Inline admin for photos within an album.
    """
    model = Photo
    extra = 1
    fields = ['title', 'caption', 'original_image', 'order', 'thumbnail_preview']
    readonly_fields = ['thumbnail_preview']
    ordering = ['order', '-created_at']
    
    def thumbnail_preview(self, obj):
        """Display thumbnail preview in inline form."""
        if obj.thumbnail:
            return mark_safe(f'<img src="{obj.thumbnail.url}" width="50" height="50" style="object-fit: cover;" />')
        elif obj.original_image:
            return mark_safe(f'<img src="{obj.original_image.url}" width="50" height="50" style="object-fit: cover;" />')
        return "No image"
    thumbnail_preview.short_description = 'Preview'


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    """
    Admin configuration for Album model.
    """
    list_display = ['title', 'is_published', 'photo_count', 'cover_preview', 'created_at', 'order']
    list_filter = ['is_published', 'created_at', 'updated_at']
    search_fields = ['title', 'description']
    list_editable = ['is_published', 'order']
    ordering = ['order', '-created_at']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'photo_count', 'cover_preview_large']
    inlines = [PhotoInline]
    
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
    )
    
    def photo_count(self, obj):
        """Display the number of photos in the album."""
        count = obj.photos.count()
        url = reverse('admin:photos_photo_changelist') + f'?album__id__exact={obj.id}'
        return mark_safe(f'<a href="{url}">{count} photo(s)</a>')
    photo_count.short_description = 'Photos'
    photo_count.admin_order_field = 'photos__count'
    
    def cover_preview(self, obj):
        """Display small cover image preview in list view."""
        if obj.cover_image:
            return mark_safe(f'<img src="{obj.cover_image.url}" width="50" height="50" style="object-fit: cover;" />')
        return "No cover"
    cover_preview.short_description = 'Cover'
    
    def cover_preview_large(self, obj):
        """Display larger cover image preview in detail view."""
        if obj.cover_image:
            return mark_safe(f'<img src="{obj.cover_image.url}" width="200" style="max-height: 200px; object-fit: cover;" />')
        return "No cover image set"
    cover_preview_large.short_description = 'Current Cover'
    
    def get_queryset(self, request):
        """Optimize queryset with photo count."""
        queryset = super().get_queryset(request)
        return queryset.prefetch_related('photos')
    
    actions = ['publish_albums', 'unpublish_albums', 'regenerate_thumbnails']
    
    def publish_albums(self, request, queryset):
        """Bulk action to publish selected albums."""
        count = queryset.update(is_published=True)
        self.message_user(request, f'{count} album(s) published successfully.')
    publish_albums.short_description = 'Publish selected albums'
    
    def unpublish_albums(self, request, queryset):
        """Bulk action to unpublish selected albums."""
        count = queryset.update(is_published=False)
        self.message_user(request, f'{count} album(s) unpublished successfully.')
    unpublish_albums.short_description = 'Unpublish selected albums'
    
    def regenerate_thumbnails(self, request, queryset):
        """Bulk action to regenerate thumbnails for all photos in selected albums."""
        from .utils import generate_thumbnail, get_thumbnail_filename
        
        total_processed = 0
        total_failed = 0
        
        for album in queryset:
            for photo in album.photos.all():
                if photo.original_image:
                    try:
                        thumbnail_file = generate_thumbnail(photo.original_image)
                        if thumbnail_file:
                            thumb_filename = get_thumbnail_filename(photo.original_image.name)
                            photo.thumbnail.save(thumb_filename, thumbnail_file, save=True)
                            total_processed += 1
                        else:
                            total_failed += 1
                    except Exception as e:
                        total_failed += 1
        
        self.message_user(
            request, 
            f'Regenerated {total_processed} thumbnail(s). {total_failed} failed.'
        )
    regenerate_thumbnails.short_description = 'Regenerate thumbnails for selected albums'


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    """
    Admin configuration for Photo model.
    """
    list_display = ['title_display', 'album', 'thumbnail_preview', 'order', 'created_at']
    list_filter = ['album', 'created_at']
    search_fields = ['title', 'caption', 'album__title']
    autocomplete_fields = ['album']
    list_editable = ['order']
    ordering = ['album', 'order', '-created_at']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'thumbnail_preview_large', 'original_preview_large']
    list_per_page = 50
    
    fieldsets = (
        ('Photo Information', {
            'fields': ('album', 'title', 'caption')
        }),
        ('Images', {
            'fields': ('original_image', 'original_preview_large', 'thumbnail', 'thumbnail_preview_large')
        }),
        ('Ordering', {
            'fields': ('order',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def title_display(self, obj):
        """Display title or fallback text."""
        return obj.title or f"Untitled (ID: {obj.id})"
    title_display.short_description = 'Title'
    title_display.admin_order_field = 'title'
    
    def thumbnail_preview(self, obj):
        """Display thumbnail preview in list view."""
        if obj.thumbnail:
            return mark_safe(f'<img src="{obj.thumbnail.url}" width="50" height="50" style="object-fit: cover;" />')
        elif obj.original_image:
            return mark_safe(f'<img src="{obj.original_image.url}" width="50" height="50" style="object-fit: cover;" />')
        return "No thumbnail"
    thumbnail_preview.short_description = 'Preview'
    
    def thumbnail_preview_large(self, obj):
        """Display larger thumbnail preview in detail view."""
        if obj.thumbnail:
            return mark_safe(f'<img src="{obj.thumbnail.url}" width="200" style="max-height: 200px; object-fit: cover;" />')
        return "No thumbnail generated"
    thumbnail_preview_large.short_description = 'Thumbnail Preview'
    
    def original_preview_large(self, obj):
        """Display original image preview in detail view."""
        if obj.original_image:
            return mark_safe(
                f'<img src="{obj.original_image.url}" width="400" style="max-height: 400px; object-fit: contain;" />'
                f'<br><small>Click to view full size: <a href="{obj.original_image.url}" target="_blank">{obj.original_image.url}</a></small>'
            )
        return "No image"
    original_preview_large.short_description = 'Original Image Preview'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        queryset = super().get_queryset(request)
        return queryset.select_related('album')
    
    actions = ['regenerate_thumbnails', 'move_to_album']
    
    def regenerate_thumbnails(self, request, queryset):
        """Bulk action to regenerate thumbnails for selected photos."""
        from .utils import generate_thumbnail, get_thumbnail_filename
        
        processed = 0
        failed = 0
        
        for photo in queryset:
            if photo.original_image:
                try:
                    thumbnail_file = generate_thumbnail(photo.original_image)
                    if thumbnail_file:
                        thumb_filename = get_thumbnail_filename(photo.original_image.name)
                        photo.thumbnail.save(thumb_filename, thumbnail_file, save=True)
                        processed += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
        
        self.message_user(request, f'Regenerated {processed} thumbnail(s). {failed} failed.')
    regenerate_thumbnails.short_description = 'Regenerate thumbnails for selected photos'
    
    def move_to_album(self, request, queryset):
        """Placeholder for moving photos to different album."""
        # This would require a custom intermediate page to select the target album
        self.message_user(request, 'This feature requires custom implementation.')
    move_to_album.short_description = 'Move to different album'


# Customize admin site header and title
admin.site.site_header = "Aaron Spindler Photo Gallery Admin"
admin.site.site_title = "Photo Gallery Admin"
admin.site.index_title = "Photo Gallery Management"