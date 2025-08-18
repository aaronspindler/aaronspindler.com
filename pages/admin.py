from django.contrib import admin
from django.shortcuts import redirect
from .models import PageVisit, Photo, PhotoAlbum
from django.urls import path
from django.utils.html import format_html
import requests
import json

LOCAL_IPS = ['127.0.0.1', '10.0.2.2', '10.0.1.5']

@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display = ('page_name', 'ip_address', 'created_at', 'geo_data')
    list_filter = ('page_name', 'created_at', 'ip_address')
    search_fields = ('page_name', 'ip_address', 'geo_data')
    readonly_fields = ('created_at', 'ip_address', 'page_name', 'geo_data')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "geolocate_ips/",
                self.admin_site.admin_view(
                    self.geolocate_ips,
                ),
                name="pages_pagevisit_geolocate_ips",
            ),
            path(
                "clean_local_ips/",
                self.admin_site.admin_view(
                    self.clean_local_ips,
                ),
                name="pages_pagevisit_clean_local_ips",
            ),
            
        ]
        return custom_urls + urls

    def geolocate_ips(self, request):
        ips = list(PageVisit.objects.filter(geo_data__isnull=True).values_list('ip_address', flat=True).distinct())
        ips = [ip for ip in ips if ip not in LOCAL_IPS]
        
        print(f"Geolocating {len(ips)} IP addresses")
        print(ips)
        
        for i in range(0, len(ips), 100):
            chunk = ips[i:i+100]
            formatted_chunk = json.dumps(chunk)
            try:
                response = requests.post('http://ip-api.com/batch', data=formatted_chunk)
                data = response.json()
                for response in data:
                    if response['status'] == 'success':
                        ip = response.pop('query')
                        response.pop('status')
                        PageVisit.objects.filter(ip_address=ip).update(geo_data=response)
            except Exception as e:
                print(f"Error geolocating chunk {i//100 + 1}: {e}")
        return redirect('admin:pages_pagevisit_changelist')
    
    def clean_local_ips(self, request):
        PageVisit.objects.filter(ip_address__in=LOCAL_IPS).delete()
        self.message_user(request, "Local IP addresses cleaned.")
        return redirect('admin:pages_pagevisit_changelist')


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
