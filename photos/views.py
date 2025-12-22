from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

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

    album_photos = (
        album.album_photos.select_related("photo")
        .only(
            "is_featured",
            "display_order",
            "added_at",
            "photo__id",
            "photo__image",
            "photo__image_thumbnail",
            "photo__image_preview",
            "photo__original_filename",
            "photo__date_taken",
            "photo__created_at",
        )
        .order_by(
            "display_order",
            "-photo__date_taken",
            "-photo__created_at",
        )
    )

    photos_data = [
        {
            "photo": ap.photo,
            "is_featured": ap.is_featured,
        }
        for ap in album_photos
    ]

    cover_photo = None
    for ap in album_photos:
        if ap.is_featured:
            cover_photo = ap.photo
            break
    if not cover_photo and album_photos:
        cover_photo = album_photos[0].photo

    page_og_image = None
    if cover_photo:
        image_url = cover_photo.get_image_url("thumbnail") or cover_photo.get_image_url("preview")
        if image_url:
            page_og_image = request.build_absolute_uri(image_url)

    og_description = album.description or "View photos from this album"

    return render(
        request,
        "photos/album_detail.html",
        {
            "album": album,
            "photos_data": photos_data,
            "allow_downloads": album.allow_downloads,
            "share_token": token if token else None,
            "page_og_title": f"{album.title} - Photo Album",
            "page_og_description": og_description,
            "page_og_image": page_og_image,
            "page_meta_description": og_description,
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
    token = request.GET.get("token")

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


@staff_member_required
@require_http_methods(["POST"])
def upload_photo_api(request):
    try:
        if "photo" not in request.FILES:
            return JsonResponse({"error": "No photo file provided"}, status=400)

        photo_file = request.FILES["photo"]
        album_id = request.POST.get("album_id")

        album = None
        if album_id:
            try:
                album = PhotoAlbum.objects.get(id=album_id)
            except PhotoAlbum.DoesNotExist:
                return JsonResponse({"error": f"Album with ID {album_id} not found"}, status=400)

        photo = Photo()
        photo.image.save(photo_file.name, photo_file, save=False)

        # and raise ValidationError if duplicate found
        try:
            photo.save(skip_processing=True)
        except Exception as e:
            # Check if it's a duplicate error
            if "duplicate" in str(e).lower():
                return JsonResponse(
                    {
                        "error": "duplicate",
                        "message": str(e),
                    },
                    status=409,
                )
            raise

        from photos.tasks import process_photo_async

        process_photo_async.delay(photo.id)

        if album:
            album.photos.add(photo)

        return JsonResponse(
            {
                "success": True,
                "photo_id": photo.id,
                "filename": photo_file.name,
                "status": "processing",
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@staff_member_required
@require_http_methods(["GET"])
def photo_status_api(request, photo_id):
    try:
        photo = Photo.objects.get(id=photo_id)
        return JsonResponse(
            {
                "photo_id": photo.id,
                "status": photo.processing_status,
                "thumbnail_url": photo.get_image_url("preview") if photo.processing_status == "complete" else None,
            }
        )
    except Photo.DoesNotExist:
        return JsonResponse({"error": "Photo not found"}, status=404)


@require_http_methods(["GET"])
def photo_exif_api(request, slug, photo_id):
    token = request.GET.get("token")

    if token:
        album = get_object_or_404(PhotoAlbum, slug=slug, share_token=token, is_private=True)
    elif request.user.is_authenticated and request.user.is_staff:
        album = get_object_or_404(PhotoAlbum, slug=slug)
    else:
        album = get_object_or_404(PhotoAlbum, slug=slug, is_private=False)

    photo = get_object_or_404(
        Photo.objects.only(
            "id",
            "camera_make",
            "camera_model",
            "lens_model",
            "focal_length",
            "aperture",
            "shutter_speed",
            "iso",
            "date_taken",
        ),
        id=photo_id,
    )

    if not album.photos.filter(id=photo_id).exists():
        return JsonResponse({"error": "Photo not found in this album"}, status=404)

    camera = f"{photo.camera_make} {photo.camera_model}".strip()
    date_taken = photo.date_taken.strftime("%B %d, %Y") if photo.date_taken else ""

    return JsonResponse(
        {
            "photo_id": photo.id,
            "exif": {
                "camera": camera,
                "lens": photo.lens_model or "",
                "focalLength": photo.focal_length or "",
                "aperture": photo.aperture or "",
                "shutterSpeed": photo.shutter_speed or "",
                "iso": str(photo.iso) if photo.iso else "",
                "dateTaken": date_taken,
            },
        }
    )
