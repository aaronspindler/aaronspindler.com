from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from .forms import PhotoAlbumForm, PhotoBulkUploadForm
from .models import AlbumPhoto, Photo, PhotoAlbum


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = (
        "image_preview",
        "get_display_name",
        "title",
        "processing_status_display",
        "file_info",
        "camera_info",
        "has_duplicates",
        "created_at",
    )
    list_filter = ("processing_status", "created_at", "updated_at", "camera_make", "camera_model")
    search_fields = (
        "title",
        "description",
        "original_filename",
        "camera_make",
        "camera_model",
        "lens_model",
        "file_hash",
        "perceptual_hash",
    )
    list_editable = ("title",)
    list_display_links = ("image_preview", "get_display_name")
    actions = ["add_to_album", "find_duplicates_action", "retry_processing"]
    readonly_fields = (
        "image_preview",
        "all_versions_preview",
        "original_filename",
        "file_size_display",
        "dimensions_display",
        # Duplicate detection fields
        "file_hash_display",
        "perceptual_hash_display",
        "duplicate_info",
        "similar_images_display",
        # EXIF readonly fields
        "camera_make",
        "camera_model",
        "lens_model",
        "focal_length",
        "aperture",
        "shutter_speed",
        "iso",
        "date_taken",
        "gps_coordinates_display",
        "gps_altitude",
        "exif_summary",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Basic Information", {"fields": ("title", "description")}),
        (
            "Image Upload",
            {
                "fields": ("image",),
                "description": "Upload a new image. Optimized versions will be created automatically. Duplicate detection will prevent identical images from being uploaded.",
            },
        ),
        (
            "Duplicate Detection",
            {
                "fields": (
                    "duplicate_info",
                    "similar_images_display",
                    "file_hash_display",
                    "perceptual_hash_display",
                ),
                "classes": ("collapse",),
                "description": "Information about duplicate and similar images",
            },
        ),
        (
            "Image Versions",
            {
                "fields": ("all_versions_preview",),
                "classes": ("collapse",),
            },
        ),
        (
            "Camera & Settings",
            {
                "fields": (
                    "camera_make",
                    "camera_model",
                    "lens_model",
                    "focal_length",
                    "aperture",
                    "shutter_speed",
                    "iso",
                    "date_taken",
                ),
                "classes": ("collapse",),
                "description": "EXIF metadata extracted from the image",
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "gps_coordinates_display",
                    "gps_altitude",
                ),
                "classes": ("collapse",),
                "description": "GPS location data from the image",
            },
        ),
        (
            "File Metadata",
            {
                "fields": (
                    "original_filename",
                    "file_size_display",
                    "dimensions_display",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Full EXIF Data",
            {
                "fields": ("exif_summary",),
                "classes": ("collapse",),
                "description": "Complete EXIF metadata in JSON format",
            },
        ),
    )

    @admin.display(description="Name")
    def get_display_name(self, obj):
        """Get display name for the photo."""
        if obj.title:
            return obj.title
        elif obj.original_filename:
            return obj.original_filename
        else:
            return f"Photo {obj.pk}"

    @admin.display(description="Status", ordering="processing_status")
    def processing_status_display(self, obj):
        """Display the processing status with colored indicators."""
        status_map = {
            "pending": ("🟡", "Pending", "#ffc107"),
            "processing": ("🔵", "Processing...", "#17a2b8"),
            "complete": ("🟢", "Complete", "#28a745"),
            "failed": ("🔴", "Failed", "#dc3545"),
        }
        icon, text, color = status_map.get(obj.processing_status, ("⚪", "Unknown", "#6c757d"))
        return format_html('<span style="color: {};">{} {}</span>', color, icon, text)

    @admin.action(description="Add selected photos to album")
    def add_to_album(self, request, queryset):
        """Batch action to add selected photos to an album."""

        albums = PhotoAlbum.objects.all()
        if not albums:
            messages.warning(request, "No albums exist. Please create an album first.")
            return

        selected = request.POST.getlist("_selected_action")
        if selected:
            messages.info(
                request,
                f"Selected {len(selected)} photos. To add to an album, edit the album and select these photos.",
            )

    @admin.display(description="Preview")
    def image_preview(self, obj):
        try:
            if obj.image_display:
                return format_html(
                    '<img src="{}" style="max-width: 150px; max-height: 150px;" />',
                    obj.image_display.url,
                )
            elif obj.image_optimized:
                return format_html(
                    '<img src="{}" style="max-width: 150px; max-height: 150px;" />',
                    obj.image_optimized.url,
                )
            elif obj.image:
                return format_html(
                    '<img src="{}" style="max-width: 150px; max-height: 150px;" />',
                    obj.image.url,
                )
        except (ValueError, AttributeError):
            # Image field exists but file is missing or URL cannot be generated
            # This is expected when images are being processed or files are moved
            return "No image"
        return "No image"

    @admin.display(description="All Image Versions")
    def all_versions_preview(self, obj):
        """Display all available image versions with their sizes."""
        if not obj.image:
            return "No images available"

        from django.utils.html import format_html
        from django.utils.safestring import mark_safe

        html_parts = []

        # Display each version with its info
        versions = [
            ("Display (Smart Cropped)", obj.image_display, "1200x800"),
            (
                "Optimized Full Size",
                obj.image_optimized,
                f"{obj.width}x{obj.height}" if obj.width else "Full Size",
            ),
            (
                "Original",
                obj.image,
                f"{obj.width}x{obj.height}" if obj.width else "Original",
            ),
        ]

        for label, image_field, dimensions in versions:
            if image_field:
                try:
                    url = image_field.url
                    try:
                        file_size = image_field.size
                    except (ValueError, AttributeError, FileNotFoundError):
                        file_size = 0

                    size_kb = file_size / 1024 if file_size else 0

                    html_parts.append(
                        format_html(
                            """
                        <div style="display: inline-block; margin: 10px; text-align: center;">
                            <strong>{}</strong><br>
                            <img src="{}" style="max-width: 200px; max-height: 200px; border: 1px solid #ddd; padding: 5px;" /><br>
                            <small>{} • {:.1f} KB</small>
                        </div>
                        """,
                            label,
                            url,
                            dimensions,
                            size_kb,
                        )
                    )
                except (ValueError, AttributeError, FileNotFoundError):
                    html_parts.append(
                        format_html(
                            """<div style="display: inline-block; margin: 10px; text-align: center;">
                            <strong>{}</strong><br>
                            <small style="color: #999;">File not found</small>
                        </div>""",
                            label,
                        )
                    )

        if html_parts:
            return mark_safe(  # nosec B703 B308 - Content is safely escaped via format_html
                f'<div style="background: #f9f9f9; padding: 10px; border-radius: 5px;">{"".join(html_parts)}</div>'
            )
        else:
            return "No versions available"

    @admin.display(description="File Info")
    def file_info(self, obj):
        """Display file size and dimensions in list view."""
        try:
            if obj.file_size:
                # Convert to plain float to avoid SafeString/format_html issues
                size_mb = float(obj.file_size) / (1024 * 1024)
                size_str = f"{size_mb:.1f}"
                width_str = str(int(obj.width)) if obj.width else "?"
                height_str = str(int(obj.height)) if obj.height else "?"
                return format_html(
                    "<span>{} MB</span> • <span>{}×{}</span>",
                    size_str,
                    width_str,
                    height_str,
                )
        except (TypeError, ValueError, AttributeError) as e:
            print(f"Error formatting file info for photo {obj.pk}: {e}")

        return "—"

    @admin.display(description="Original File Size")
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

    @admin.display(description="Original Dimensions")
    def dimensions_display(self, obj):
        """Display image dimensions."""
        if obj.width and obj.height:
            return f"{obj.width} × {obj.height} pixels"
        return "Unknown"

    @admin.display(description="Camera")
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

    @admin.display(description="GPS Coordinates")
    def gps_coordinates_display(self, obj):
        """Display GPS coordinates in a readable format."""
        if obj.gps_latitude and obj.gps_longitude:
            lat_dir = "N" if obj.gps_latitude >= 0 else "S"
            lon_dir = "E" if obj.gps_longitude >= 0 else "W"
            maps_url = f"https://www.google.com/maps?q={obj.gps_latitude},{obj.gps_longitude}"

            return format_html(
                '{:.6f}°{} {:.6f}°{} <a href="{}" target="_blank">View on Map</a>',
                abs(obj.gps_latitude),
                lat_dir,
                abs(obj.gps_longitude),
                lon_dir,
                maps_url,
            )
        return "No GPS data"

    @admin.display(description="Full EXIF Data")
    def exif_summary(self, obj):
        """Display full EXIF data in a formatted way."""
        if obj.exif_data:
            import json

            try:
                formatted_json = json.dumps(obj.exif_data, indent=2, sort_keys=True)
                return format_html(
                    '<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; '
                    'max-height: 400px; overflow-y: auto; font-size: 11px;">{}</pre>',
                    formatted_json,
                )
            except Exception:
                # Catch any JSON formatting errors and return raw data
                return str(obj.exif_data)
        return "No EXIF data available"

    @admin.display(description="Duplicates")
    def has_duplicates(self, obj):
        """Check if this photo has duplicates."""
        if obj.file_hash:
            duplicate_count = Photo.objects.filter(file_hash=obj.file_hash).exclude(pk=obj.pk).count()

            if duplicate_count > 0:
                return format_html(
                    '<span style="color: red;">⚠️ {} duplicate(s)</span>',
                    duplicate_count,
                )

        # Check for similar images
        if obj.perceptual_hash:
            similar = obj.get_similar_images(threshold=5)
            if similar:
                return format_html('<span style="color: orange;">≈ {} similar</span>', len(similar))

        return format_html('<span style="color: green;">✓ Unique</span>')

    @admin.display(description="File Hash (SHA-256)")
    def file_hash_display(self, obj):
        """Display file hash with truncation."""
        if obj.file_hash:
            return format_html(
                '<code style="font-family: monospace; background: #f5f5f5; padding: 2px 5px; border-radius: 3px;">{}</code>',
                (obj.file_hash[:16] + "..." if len(obj.file_hash) > 16 else obj.file_hash),
            )
        return "Not computed"

    @admin.display(description="Perceptual Hash")
    def perceptual_hash_display(self, obj):
        """Display perceptual hash."""
        if obj.perceptual_hash:
            return format_html(
                '<code style="font-family: monospace; background: #f5f5f5; padding: 2px 5px; border-radius: 3px;">{}</code>',
                obj.perceptual_hash,
            )
        return "Not computed"

    @admin.display(description="Exact Duplicates")
    def duplicate_info(self, obj):
        """Display information about exact duplicates."""
        if not obj.file_hash:
            return "Hash not computed"

        duplicates = Photo.objects.filter(file_hash=obj.file_hash).exclude(pk=obj.pk).order_by("created_at")

        if not duplicates:
            return format_html('<span style="color: green;">No exact duplicates found</span>')

        html_parts = [
            '<div style="background: #fff3cd; padding: 10px; border-radius: 5px; border: 1px solid #ffc107;">'
        ]
        html_parts.append("<strong>⚠️ Exact duplicates found:</strong><br/>")

        for dup in duplicates[:5]:
            html_parts.append(
                format_html(
                    '• <a href="/admin/photos/photo/{}/change/">Photo #{}</a>: "{}" (uploaded {})<br/>',
                    dup.pk,
                    dup.pk,
                    dup,
                    dup.created_at.strftime("%Y-%m-%d %H:%M"),
                )
            )

        if duplicates.count() > 5:
            html_parts.append(f"... and {duplicates.count() - 5} more")

        html_parts.append("</div>")
        return format_html("".join(html_parts))

    @admin.display(description="Similar Images")
    def similar_images_display(self, obj):
        """Display information about similar images."""
        if not obj.perceptual_hash:
            return "Perceptual hash not computed"

        similar = obj.get_similar_images(threshold=10)  # Slightly higher threshold for display

        if not similar:
            return format_html('<span style="color: green;">No similar images found</span>')

        html_parts = [
            '<div style="background: #e7f3ff; padding: 10px; border-radius: 5px; border: 1px solid #007bff;">'
        ]
        html_parts.append("<strong>Similar images found:</strong><br/>")

        for photo, distance in similar[:5]:
            # Convert Hamming distance to similarity percentage (64 bits total)
            similarity = 100 - (distance * 100 / 64)
            html_parts.append(
                format_html(
                    '• <a href="/admin/photos/photo/{}/change/">Photo #{}</a>: "{}" ({:.1f}% similar)<br/>',
                    photo.pk,
                    photo.pk,
                    photo,
                    similarity,
                )
            )

        if len(similar) > 5:
            html_parts.append(f"... and {len(similar) - 5} more")

        html_parts.append("</div>")
        return format_html("".join(html_parts))

    @admin.action(description="Find duplicates among selected photos")
    def find_duplicates_action(self, request, queryset):
        """Action to find duplicates among selected photos."""
        from collections import defaultdict

        # Group by file hash
        hash_groups = defaultdict(list)
        for photo in queryset:
            if photo.file_hash:
                hash_groups[photo.file_hash].append(photo)

        # Report duplicates
        duplicate_count = 0
        for _file_hash, photos in hash_groups.items():
            if len(photos) > 1:
                duplicate_count += 1
                photos_str = ", ".join([f"#{p.pk}" for p in photos])
                messages.warning(
                    request,
                    f"Duplicate group {duplicate_count}: Photos {photos_str} have identical content",
                )

        if duplicate_count == 0:
            messages.success(request, "No duplicates found among selected photos")
        else:
            messages.info(request, f"Found {duplicate_count} group(s) of duplicates")

    @admin.action(description="Retry processing for selected photos")
    def retry_processing(self, request, queryset):
        """Retry processing for photos that failed or are pending."""
        from photos.tasks import process_photo_async

        retryable = queryset.filter(processing_status__in=["pending", "failed"])
        count = 0
        for photo in retryable:
            process_photo_async.delay(photo.pk)
            count += 1

        if count > 0:
            messages.success(request, f"Queued {count} photo(s) for reprocessing")
        else:
            messages.info(request, "No photos needed reprocessing")

    def get_urls(self):
        """Add custom URLs for bulk upload."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "bulk-upload/",
                self.admin_site.admin_view(self.bulk_upload_view),
                name="photos_photo_bulk_upload",
            ),
        ]
        return custom_urls + urls

    def bulk_upload_view(self, request):
        """View for bulk uploading photos."""
        if request.method == "POST":
            form = PhotoBulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                result = form.save(skip_duplicates=True)

                # Prepare messages
                if result["created"]:
                    messages.success(
                        request,
                        f"Successfully uploaded {len(result['created'])} photo(s).",
                    )

                if result["skipped"]:
                    skipped_msg = "Skipped duplicates: "
                    for filename, reason in result["skipped"][:5]:
                        skipped_msg += f"\n• {filename}: {reason}"
                    if len(result["skipped"]) > 5:
                        skipped_msg += f"\n... and {len(result['skipped']) - 5} more"
                    messages.warning(request, skipped_msg)

                if result["errors"]:
                    error_msg = "Failed uploads: "
                    for filename, error in result["errors"][:5]:
                        error_msg += f"\n• {filename}: {error}"
                    if len(result["errors"]) > 5:
                        error_msg += f"\n... and {len(result['errors']) - 5} more"
                    messages.error(request, error_msg)

                return redirect("admin:photos_photo_changelist")
        else:
            form = PhotoBulkUploadForm()

        context = {
            "form": form,
            "title": "Bulk Upload Photos",
            "site_title": self.admin_site.site_title,
            "site_header": self.admin_site.site_header,
            "has_permission": True,
            "opts": self.model._meta,
            "app_label": self.model._meta.app_label,
        }
        return render(request, "admin/photos/photo/bulk_upload.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["bulk_upload_url"] = reverse("admin:photos_photo_bulk_upload")
        return super().changelist_view(request, extra_context=extra_context)


class AlbumPhotoInline(admin.TabularInline):
    model = AlbumPhoto
    extra = 0
    fields = ("photo", "is_featured", "display_order", "photo_preview")
    readonly_fields = ("photo_preview",)
    autocomplete_fields = ["photo"]
    ordering = ["-is_featured", "display_order", "-photo__date_taken"]

    @admin.display(description="Preview")
    def photo_preview(self, obj):
        if obj.photo and obj.photo.image_display:
            featured_badge = (
                ' <span style="background: gold; padding: 2px 6px; border-radius: 4px; font-size: 10px;">FEATURED</span>'
                if obj.is_featured
                else ""
            )
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 75px;" />{}',
                obj.photo.image_display.url,
                featured_badge,
            )
        return "No image"


@admin.register(AlbumPhoto)
class AlbumPhotoAdmin(admin.ModelAdmin):
    list_display = ("photo_preview", "photo", "album", "is_featured", "display_order", "added_at")
    list_filter = ("is_featured", "album")
    list_editable = ("is_featured", "display_order")
    search_fields = ("photo__title", "photo__original_filename", "album__title")
    autocomplete_fields = ["album", "photo"]
    readonly_fields = ("photo_preview",)

    @admin.display(description="Preview")
    def photo_preview(self, obj):
        if obj.photo and obj.photo.image_display:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 75px;" />',
                obj.photo.image_display.url,
            )
        return "No image"


@admin.register(PhotoAlbum)
class PhotoAlbumAdmin(admin.ModelAdmin):
    form = PhotoAlbumForm
    list_display = (
        "title",
        "slug",
        "photo_count",
        "privacy_status",
        "is_private",
        "downloads_status",
        "allow_downloads",
        "zip_status",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_private", "allow_downloads", "zip_generation_status", "created_at", "updated_at")
    list_editable = ("is_private", "allow_downloads")
    search_fields = ("title", "description", "slug")
    readonly_fields = (
        "created_at",
        "updated_at",
        "share_url_display",
        "share_analytics",
        "zip_status_display",
        "zip_download_link",
    )
    prepopulated_fields = {"slug": ("title",)}
    inlines = [AlbumPhotoInline]
    actions = ["regenerate_zip"]

    fieldsets = (
        ("Basic Information", {"fields": ("title", "slug", "description")}),
        (
            "Settings",
            {
                "fields": ("is_private", "allow_downloads"),
                "description": "Privacy and download settings for this album",
            },
        ),
        (
            "External Sharing (Private Albums Only)",
            {
                "fields": ("share_url_display", "share_analytics"),
                "description": "Private albums can be shared externally using the share link below",
            },
        ),
        (
            "ZIP Download",
            {
                "fields": ("zip_status_display", "zip_download_link"),
                "description": "Album ZIP file for bulk download (regenerates automatically when photos change)",
            },
        ),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description="Photos")
    def photo_count(self, obj):
        return obj.photos.count()

    @admin.display(
        description="Privacy",
        ordering="is_private",
    )
    def privacy_status(self, obj):
        if obj.is_private:
            return format_html('<span style="color: #dc3545;">🔒 Private</span>')
        else:
            return format_html('<span style="color: #28a745;">🌐 Public</span>')

    @admin.display(
        description="Downloads",
        ordering="allow_downloads",
    )
    def downloads_status(self, obj):
        if obj.allow_downloads:
            return format_html('<span style="color: #28a745;">✓ Enabled</span>')
        else:
            return format_html('<span style="color: #6c757d;">✗ Disabled</span>')

    @admin.display(description="ZIP")
    def zip_status(self, obj):
        status_map = {
            "none": ("⚪", "Not generated"),
            "pending": ("🟡", "Pending"),
            "generating": ("🔵", "Generating..."),
            "ready": ("🟢", "Ready"),
            "failed": ("🔴", "Failed"),
        }
        icon, text = status_map.get(obj.zip_generation_status, ("⚪", "Unknown"))
        return format_html('<span title="{}">{}</span>', text, icon)

    @admin.display(description="ZIP File Status")
    def zip_status_display(self, obj):
        if not obj.allow_downloads:
            return "Downloads disabled for this album"

        if obj.zip_generation_status == "none":
            return "No ZIP generated yet"
        elif obj.zip_generation_status == "pending":
            return format_html('<span style="color: orange;">ZIP generation pending...</span>')
        elif obj.zip_generation_status == "generating":
            return format_html('<span style="color: blue;">Generating ZIP...</span>')
        elif obj.zip_generation_status == "failed":
            return format_html('<span style="color: red;">ZIP generation failed</span>')
        elif obj.zip_generation_status == "ready":
            size_mb = obj.zip_file_size / (1024 * 1024) if obj.zip_file_size else 0
            generated = obj.zip_generated_at.strftime("%Y-%m-%d %H:%M") if obj.zip_generated_at else "Unknown"
            return format_html(
                '<span style="color: green;">Ready</span><br><small>Size: {:.1f} MB | Generated: {}</small>',
                size_mb,
                generated,
            )
        return "Unknown status"

    @admin.display(description="Download ZIP")
    def zip_download_link(self, obj):
        if obj.zip_file and obj.zip_generation_status == "ready":
            return format_html('<a href="{}" class="button" download>Download ZIP</a>', obj.zip_file.url)
        return "—"

    @admin.action(description="Regenerate ZIP files for selected albums")
    def regenerate_zip(self, request, queryset):
        from photos.tasks import generate_album_zip

        count = 0
        for album in queryset.filter(allow_downloads=True):
            generate_album_zip.delay(album.id, force=True)
            count += 1

        messages.success(request, f"Scheduled ZIP regeneration for {count} album(s)")

    @admin.display(description="Share Link")
    def share_url_display(self, obj):
        if not obj.is_private:
            return "Public albums don't need share links"

        base_url = f"https://aaronspindler.com{reverse('photos:album_detail', kwargs={'slug': obj.slug})}"
        url = f"{base_url}?token={obj.share_token}"

        return format_html(
            '<input type="text" value="{}" id="share-url-{}" readonly style="width: 400px; margin-right: 10px;">'
            "<button onclick=\"navigator.clipboard.writeText('{}'); "
            "this.innerHTML='Copied!'; setTimeout(() => this.innerHTML='Copy', 2000)\" "
            'style="cursor: pointer;">Copy</button>',
            url,
            obj.id,
            url,
        )

    @admin.display(description="Share Analytics")
    def share_analytics(self, obj):
        if not obj.is_private:
            return "—"

        if obj.share_access_count == 0:
            return "No views yet"

        last_accessed = obj.share_last_accessed.strftime("%Y-%m-%d %H:%M") if obj.share_last_accessed else "Never"
        return format_html(
            "<strong>{}</strong> views<br><small>Last accessed: {}</small>",
            obj.share_access_count,
            last_accessed,
        )
