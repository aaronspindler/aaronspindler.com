from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Photo, PhotoAlbum


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
        "-is_featured",
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

    return render(
        request,
        "photos/album_detail.html",
        {
            "album": album,
            "photos_data": photos_data,
            "photos": [ap.photo for ap in album_photos],
            "allow_downloads": album.allow_downloads,
            "share_token": token if token else None,
        },
    )


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
