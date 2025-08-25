from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Photo, PhotoAlbum
from .forms import PhotoBulkUploadForm


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'get_display_name', 'title', 'file_info', 'camera_info', 'created_at')
    list_filter = ('created_at', 'updated_at', 'camera_make', 'camera_model')
    search_fields = ('title', 'description', 'original_filename', 'camera_make', 'camera_model', 'lens_model')
    list_editable = ('title',)  # Allow inline editing of titles in list view
    list_display_links = ('image_preview', 'get_display_name')
    actions = ['add_to_album']
    readonly_fields = (
        'image_preview', 
        'all_versions_preview',
        'original_filename',
        'file_size_display',
        'dimensions_display',
        # EXIF readonly fields
        'camera_make',
        'camera_model',
        'lens_model',
        'focal_length',
        'aperture',
        'shutter_speed',
        'iso',
        'date_taken',
        'gps_coordinates_display',
        'gps_altitude',
        'exif_summary',
        'created_at', 
        'updated_at'
    )
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description')
        }),
        ('Image Upload', {
            'fields': ('image',),
            'description': 'Upload a new image. Optimized versions will be created automatically.'
        }),
        ('Image Versions', {
            'fields': ('all_versions_preview',),
            'classes': ('collapse',),
        }),
        ('Camera & Settings', {
            'fields': (
                'camera_make',
                'camera_model',
                'lens_model',
                'focal_length',
                'aperture',
                'shutter_speed',
                'iso',
                'date_taken',
            ),
            'classes': ('collapse',),
            'description': 'EXIF metadata extracted from the image'
        }),
        ('Location', {
            'fields': (
                'gps_coordinates_display',
                'gps_altitude',
            ),
            'classes': ('collapse',),
            'description': 'GPS location data from the image'
        }),
        ('File Metadata', {
            'fields': (
                'original_filename',
                'file_size_display',
                'dimensions_display',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',),
        }),
        ('Full EXIF Data', {
            'fields': ('exif_summary',),
            'classes': ('collapse',),
            'description': 'Complete EXIF metadata in JSON format'
        }),
    )
    
    def get_display_name(self, obj):
        """Get display name for the photo."""
        if obj.title:
            return obj.title
        elif obj.original_filename:
            return obj.original_filename
        else:
            return f"Photo {obj.pk}"
    get_display_name.short_description = 'Name'
    
    def add_to_album(self, request, queryset):
        """Batch action to add selected photos to an album."""
        from django.contrib.admin.helpers import ActionForm
        from django import forms
        
        # Get list of albums for the intermediate form
        albums = PhotoAlbum.objects.all()
        if not albums:
            messages.warning(request, "No albums exist. Please create an album first.")
            return
        
        # For simplicity, add to the first album or show a message
        # In production, you'd want to show a form to select the album
        selected = request.POST.getlist('_selected_action')
        if selected:
            messages.info(
                request, 
                f"Selected {len(selected)} photos. To add to an album, edit the album and select these photos."
            )
    add_to_album.short_description = "Add selected photos to album"
    
    def image_preview(self, obj):
        try:
            if obj.image_thumbnail:
                return format_html(
                    '<img src="{}" style="max-width: 150px; max-height: 150px;" />',
                    obj.image_thumbnail.url
                )
            elif obj.image:
                return format_html(
                    '<img src="{}" style="max-width: 150px; max-height: 150px;" />',
                    obj.image.url
                )
        except (ValueError, AttributeError):
            pass
        return "No image"
    image_preview.short_description = 'Preview'
    
    def all_versions_preview(self, obj):
        """Display all available image versions with their sizes."""
        if not obj.image:
            return "No images available"
        
        html_parts = []
        
        # Display each version with its info
        versions = [
            ('Thumbnail', obj.image_thumbnail, '150x150'),
            ('Small', obj.image_small, '400x400'),
            ('Medium', obj.image_medium, '800x800'),
            ('Large', obj.image_large, '1920x1920'),
            ('Full', obj.image, f'{obj.width}x{obj.height}' if obj.width else 'Original'),
        ]
        
        for label, image_field, dimensions in versions:
            if image_field:
                try:
                    # Check if the file actually exists before trying to access its properties
                    url = image_field.url
                    
                    # Get file size for each version
                    try:
                        file_size = image_field.size
                    except (ValueError, AttributeError, FileNotFoundError):
                        file_size = 0
                    
                    size_kb = file_size / 1024 if file_size else 0
                    
                    html_parts.append(
                        format_html(
                            '''
                            <div style="display: inline-block; margin: 10px; text-align: center;">
                                <strong>{}</strong><br>
                                <img src="{}" style="max-width: 200px; max-height: 200px; border: 1px solid #ddd; padding: 5px;" /><br>
                                <small>{} • {:.1f} KB</small>
                            </div>
                            ''',
                            label,
                            url,
                            dimensions,
                            size_kb
                        )
                    )
                except (ValueError, AttributeError, FileNotFoundError) as e:
                    # File doesn't exist or can't generate URL
                    html_parts.append(
                        format_html(
                            '''<div style="display: inline-block; margin: 10px; text-align: center;">
                                <strong>{}</strong><br>
                                <small style="color: #999;">File not found</small>
                            </div>''',
                            label
                        )
                    )
        
        return format_html('<div style="background: #f9f9f9; padding: 10px; border-radius: 5px;">{}</div>', 
                          ''.join(html_parts)) if html_parts else "No versions available"
    
    all_versions_preview.short_description = 'All Image Versions'
    
    def file_info(self, obj):
        """Display file size and dimensions in list view."""
        if obj.file_size:
            size_mb = obj.file_size / (1024 * 1024)
            return format_html(
                '{:.1f} MB • {}×{}',
                size_mb,
                obj.width or '?',
                obj.height or '?'
            )
        return "—"
    file_info.short_description = 'File Info'
    
    def file_size_display(self, obj):
        """Display formatted file size."""
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} bytes"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.2f} MB"
        return "Unknown"
    file_size_display.short_description = 'Original File Size'
    
    def dimensions_display(self, obj):
        """Display image dimensions."""
        if obj.width and obj.height:
            return f"{obj.width} × {obj.height} pixels"
        return "Unknown"
    dimensions_display.short_description = 'Original Dimensions'
    
    def camera_info(self, obj):
        """Display camera information in list view."""
        if obj.camera_make and obj.camera_model:
            info_parts = [f"{obj.camera_make} {obj.camera_model}"]
            if obj.focal_length:
                info_parts.append(obj.focal_length)
            if obj.aperture:
                info_parts.append(obj.aperture)
            return " • ".join(info_parts)
        return "—"
    camera_info.short_description = 'Camera'
    
    def gps_coordinates_display(self, obj):
        """Display GPS coordinates in a readable format."""
        if obj.gps_latitude and obj.gps_longitude:
            lat_dir = 'N' if obj.gps_latitude >= 0 else 'S'
            lon_dir = 'E' if obj.gps_longitude >= 0 else 'W'
            
            # Create Google Maps link
            maps_url = f"https://www.google.com/maps?q={obj.gps_latitude},{obj.gps_longitude}"
            
            return format_html(
                '{:.6f}°{} {:.6f}°{} <a href="{}" target="_blank">View on Map</a>',
                abs(obj.gps_latitude),
                lat_dir,
                abs(obj.gps_longitude),
                lon_dir,
                maps_url
            )
        return "No GPS data"
    gps_coordinates_display.short_description = 'GPS Coordinates'
    
    def exif_summary(self, obj):
        """Display full EXIF data in a formatted way."""
        if obj.exif_data:
            import json
            try:
                # Pretty print the JSON data
                formatted_json = json.dumps(obj.exif_data, indent=2, sort_keys=True)
                return format_html(
                    '<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; '
                    'max-height: 400px; overflow-y: auto; font-size: 11px;">{}</pre>',
                    formatted_json
                )
            except:
                return str(obj.exif_data)
        return "No EXIF data available"
    exif_summary.short_description = 'Full EXIF Data'
    
    def get_urls(self):
        """Add custom URLs for bulk upload."""
        urls = super().get_urls()
        custom_urls = [
            path('bulk-upload/', 
                 self.admin_site.admin_view(self.bulk_upload_view), 
                 name='photos_photo_bulk_upload'),
        ]
        return custom_urls + urls
    
    def bulk_upload_view(self, request):
        """View for bulk uploading photos."""
        if request.method == 'POST':
            form = PhotoBulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                photos = form.save()
                messages.success(
                    request, 
                    f'Successfully uploaded {len(photos)} photo(s).'
                )
                return redirect('admin:photos_photo_changelist')
        else:
            form = PhotoBulkUploadForm()
        
        context = {
            'form': form,
            'title': 'Bulk Upload Photos',
            'site_title': self.admin_site.site_title,
            'site_header': self.admin_site.site_header,
            'has_permission': True,
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
        }
        return render(request, 'admin/photos/photo/bulk_upload.html', context)
    
    def changelist_view(self, request, extra_context=None):
        """Override to add bulk upload button."""
        extra_context = extra_context or {}
        extra_context['bulk_upload_url'] = reverse('admin:photos_photo_bulk_upload')
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(PhotoAlbum)
class PhotoAlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'photo_count', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'description')
    filter_horizontal = ('photos',)
    readonly_fields = ('created_at', 'updated_at')
    
    def photo_count(self, obj):
        return obj.photos.count()
    photo_count.short_description = 'Number of Photos'