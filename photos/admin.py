from django.contrib import admin
from django.utils.html import format_html
from .models import Photo, PhotoAlbum


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('title', 'image_preview', 'file_info', 'camera_info', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at', 'camera_make', 'camera_model')
    search_fields = ('title', 'description', 'camera_make', 'camera_model', 'lens_model')
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
    
    def image_preview(self, obj):
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
                    # Get file size for each version
                    file_size = image_field.size if hasattr(image_field, 'size') else 0
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
                            image_field.url,
                            dimensions,
                            size_kb
                        )
                    )
                except:
                    pass
        
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