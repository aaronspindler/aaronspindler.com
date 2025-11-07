from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Photo, PhotoAlbum


def album_detail(request, slug):
    if request.user.is_authenticated and request.user.is_staff:
        album = get_object_or_404(PhotoAlbum, slug=slug)
    else:
        album = get_object_or_404(PhotoAlbum, slug=slug, is_private=False)

    photos = album.photos.all().order_by("-date_taken", "-created_at")

    return render(
        request,
        "photos/album_detail.html",
        {"album": album, "photos": photos, "allow_downloads": album.allow_downloads},
    )


def download_photo(request, slug, photo_id):
    """Download a single photo from an album."""
    if request.user.is_authenticated and request.user.is_staff:
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
            raise Http404("Error accessing photo file from S3")

    raise Http404("Photo has no image file")
