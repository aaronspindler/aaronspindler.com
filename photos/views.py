import json

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import AlbumPhoto, Photo, PhotoAlbum


def album_detail(request, slug):
    token = request.GET.get("token")

    if token:
        album = get_object_or_404(PhotoAlbum, slug=slug, share_token=token, is_private=True)
        album.share_access_count += 1
        album.share_last_accessed = timezone.now()
        album.save(update_fields=["share_access_count", "share_last_accessed"])
    elif request.user.is_authenticated and request.user.is_staff:
        album = get_object_or_404(PhotoAlbum, slug=slug)
    else:
        album = get_object_or_404(PhotoAlbum, slug=slug, is_private=False)

    album_photos = album.album_photos.select_related("photo").order_by(
        "display_order",
        "-photo__date_taken",
        "-photo__created_at",
    )

    photos_data = [
        {
            "photo": ap.photo,
            "is_featured": ap.is_featured,
        }
        for ap in album_photos
    ]

    # Determine cover photo for OG image (first featured photo or first photo)
    cover_photo = None
    for ap in album_photos:
        if ap.is_featured:
            cover_photo = ap.photo
            break
    if not cover_photo and album_photos:
        cover_photo = album_photos[0].photo

    # Build absolute URL for OG image
    page_og_image = None
    if cover_photo:
        image_url = cover_photo.get_image_url("optimized") or cover_photo.get_image_url("gallery_cropped")
        if image_url:
            page_og_image = request.build_absolute_uri(image_url)

    og_description = album.description or "View photos from this album"

    return render(
        request,
        "photos/album_detail.html",
        {
            "album": album,
            "photos_data": photos_data,
            "photos": [ap.photo for ap in album_photos],
            "allow_downloads": album.allow_downloads,
            "share_token": token if token else None,
            "page_og_title": f"{album.title} - Photo Album",
            "page_og_description": og_description,
            "page_og_image": page_og_image,
            "page_meta_description": og_description,
        },
    )


def photo_detail(request, pk):
    """
    Display an individual photo page with SEO meta tags and structured data.

    Access is granted if the photo belongs to any public album, or if:
    - User is authenticated staff (can see photos in private albums)
    - A valid share token is provided for a private album containing the photo
    """
    photo = get_object_or_404(Photo, pk=pk)
    token = request.GET.get("token")

    # Find albums this photo belongs to
    all_albums = photo.albums.all()

    # Determine if user has access
    accessible_album = None
    if token:
        # Check if token matches any private album containing this photo
        accessible_album = all_albums.filter(share_token=token, is_private=True).first()
        if accessible_album:
            accessible_album.share_access_count += 1
            accessible_album.share_last_accessed = timezone.now()
            accessible_album.save(update_fields=["share_access_count", "share_last_accessed"])
    elif request.user.is_authenticated and request.user.is_staff:
        # Staff can access any photo
        accessible_album = all_albums.first()
    else:
        # Check for public albums
        accessible_album = all_albums.filter(is_private=False).first()

    if not accessible_album:
        raise Http404("Photo not found")

    # Get adjacent photos in the accessible album for navigation
    album_photos = AlbumPhoto.objects.filter(album=accessible_album).select_related("photo").order_by(
        "display_order",
        "-photo__date_taken",
        "-added_at",
    )
    photo_ids = [ap.photo_id for ap in album_photos]

    prev_photo = None
    next_photo = None
    if photo.pk in photo_ids:
        current_idx = photo_ids.index(photo.pk)
        if current_idx > 0:
            prev_photo = Photo.objects.get(pk=photo_ids[current_idx - 1])
        if current_idx < len(photo_ids) - 1:
            next_photo = Photo.objects.get(pk=photo_ids[current_idx + 1])

    # Build OG image URL
    og_image_url = None
    image_url = photo.get_image_url("optimized") or photo.get_image_url("gallery_cropped")
    if image_url:
        og_image_url = request.build_absolute_uri(image_url)

    # Build page title and description
    page_title = photo.title or photo.original_filename or f"Photo {photo.pk}"
    page_description = photo.description or _build_photo_description(photo)

    # Build structured data (schema.org ImageObject)
    structured_data = _build_photo_structured_data(request, photo, accessible_album)

    return render(
        request,
        "photos/photo_detail.html",
        {
            "photo": photo,
            "album": accessible_album,
            "albums": all_albums.filter(is_private=False) if not token else [accessible_album],
            "prev_photo": prev_photo,
            "next_photo": next_photo,
            "share_token": token,
            "allow_downloads": accessible_album.allow_downloads,
            "page_og_title": page_title,
            "page_og_description": page_description,
            "page_og_image": og_image_url,
            "page_meta_description": page_description,
            "structured_data": json.dumps(structured_data, indent=2),
        },
    )


def _build_photo_description(photo):
    """Build a description from photo metadata for SEO."""
    parts = []

    if photo.camera_make or photo.camera_model:
        camera = f"{photo.camera_make} {photo.camera_model}".strip()
        parts.append(f"Shot with {camera}")

    settings = []
    if photo.focal_length:
        settings.append(photo.focal_length)
    if photo.aperture:
        settings.append(photo.aperture)
    if photo.shutter_speed:
        settings.append(photo.shutter_speed)
    if photo.iso:
        settings.append(f"ISO {photo.iso}")

    if settings:
        parts.append(" · ".join(settings))

    if photo.date_taken:
        parts.append(f"Taken on {photo.date_taken.strftime('%B %d, %Y')}")

    return " | ".join(parts) if parts else "View this photo"


def _build_photo_structured_data(request, photo, album):
    """Build schema.org ImageObject structured data for SEO."""
    image_url = photo.get_image_url("optimized") or photo.get_image_url("original")

    data = {
        "@context": "https://schema.org",
        "@type": "ImageObject",
        "url": request.build_absolute_uri(image_url) if image_url else None,
        "contentUrl": request.build_absolute_uri(image_url) if image_url else None,
        "name": photo.title or photo.original_filename or f"Photo {photo.pk}",
    }

    if photo.description:
        data["description"] = photo.description

    if photo.width and photo.height:
        data["width"] = photo.width
        data["height"] = photo.height

    if photo.date_taken:
        data["dateCreated"] = photo.date_taken.isoformat()

    data["datePublished"] = photo.created_at.isoformat()

    if photo.camera_make or photo.camera_model:
        data["exifData"] = []
        if photo.camera_make:
            data["exifData"].append({"@type": "PropertyValue", "name": "cameraMake", "value": photo.camera_make})
        if photo.camera_model:
            data["exifData"].append({"@type": "PropertyValue", "name": "cameraModel", "value": photo.camera_model})
        if photo.iso:
            data["exifData"].append({"@type": "PropertyValue", "name": "isoSpeed", "value": str(photo.iso)})
        if photo.aperture:
            data["exifData"].append({"@type": "PropertyValue", "name": "fNumber", "value": photo.aperture})
        if photo.shutter_speed:
            data["exifData"].append({"@type": "PropertyValue", "name": "exposureTime", "value": photo.shutter_speed})
        if photo.focal_length:
            data["exifData"].append({"@type": "PropertyValue", "name": "focalLength", "value": photo.focal_length})

    if album:
        album_url = f"/photos/album/{album.slug}/"
        data["isPartOf"] = {
            "@type": "ImageGallery",
            "name": album.title,
            "url": request.build_absolute_uri(album_url),
        }

    # Add author info
    data["author"] = {
        "@type": "Person",
        "name": "Aaron Spindler",
        "url": "https://aaronspindler.com",
    }

    return data


def download_album_zip(request, slug):
    token = request.GET.get("token")

    if token:
        album = get_object_or_404(PhotoAlbum, slug=slug, share_token=token, is_private=True)
    elif request.user.is_authenticated and request.user.is_staff:
        album = get_object_or_404(PhotoAlbum, slug=slug)
    else:
        album = get_object_or_404(PhotoAlbum, slug=slug, is_private=False)

    if not album.allow_downloads:
        raise Http404("Downloads are not allowed for this album")

    if not album.zip_file or album.zip_generation_status != "ready":
        raise Http404("ZIP file is not available. Please try again later.")

    return redirect(album.zip_file.url)


def download_photo(request, slug, photo_id):
    """Download a single photo from an album."""
    # Check for share token in query params
    token = request.GET.get("token")

    # If token provided, validate it
    if token:
        album = get_object_or_404(PhotoAlbum, slug=slug, share_token=token, is_private=True)
    # Otherwise, use existing staff/public logic
    elif request.user.is_authenticated and request.user.is_staff:
        album = get_object_or_404(PhotoAlbum, slug=slug)
    else:
        album = get_object_or_404(PhotoAlbum, slug=slug, is_private=False)

    if not album.allow_downloads:
        raise Http404("Downloads are not allowed for this album")

    photo = get_object_or_404(Photo, id=photo_id)

    if album not in photo.albums.all():
        raise Http404("Photo not found in this album")

    if photo.image and hasattr(photo.image, "url"):
        try:
            import requests

            url = photo.image.url

            response = requests.get(url)
            if response.status_code == 200:
                http_response = HttpResponse(
                    response.content,
                    content_type=response.headers.get("content-type", "image/jpeg"),
                )
                filename = photo.original_filename or f"photo_{photo.id}.jpg"
                http_response["Content-Disposition"] = f'attachment; filename="{filename}"'
                return http_response
            else:
                raise Http404(f"Could not download photo from S3 (status: {response.status_code})")

        except requests.RequestException as e:
            print(f"Error downloading photo from S3: {e}")
            raise Http404("Error accessing photo file from S3") from None

    raise Http404("Photo has no image file")
