from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404, JsonResponse
from .models import PhotoAlbum, Photo
from pages.decorators import track_page_visit
import os


@track_page_visit 
def album_detail(request, slug):
    # Get the album, but ensure it's public unless user is authenticated staff
    if request.user.is_authenticated and request.user.is_staff:
        album = get_object_or_404(PhotoAlbum, slug=slug)
    else:
        album = get_object_or_404(PhotoAlbum, slug=slug, is_private=False)
    
    photos = album.photos.all().order_by('-date_taken', '-created_at')
    
    return render(request, 'photos/album_detail.html', {
        'album': album,
        'photos': photos,
        'allow_downloads': album.allow_downloads
    })


def download_photo(request, slug, photo_id):
    """Download a single photo from an album."""
    # Check album permissions
    if request.user.is_authenticated and request.user.is_staff:
        album = get_object_or_404(PhotoAlbum, slug=slug)
    else:
        album = get_object_or_404(PhotoAlbum, slug=slug, is_private=False)
    
    # Check if downloads are allowed
    if not album.allow_downloads:
        raise Http404("Downloads are not allowed for this album")
    
    # Get the photo - check if it belongs to this album
    photo = get_object_or_404(Photo, id=photo_id)
    
    # Verify the photo is in this album
    if album not in photo.albums.all():
        raise Http404("Photo not found in this album")
    
    # Get the full resolution image from S3
    if photo.image and hasattr(photo.image, 'url'):
        try:
            import requests
            url = photo.image.url
            
            # Download from S3 and proxy with download headers
            response = requests.get(url)
            if response.status_code == 200:
                http_response = HttpResponse(
                    response.content,
                    content_type=response.headers.get('content-type', 'image/jpeg')
                )
                filename = photo.original_filename or f"photo_{photo.id}.jpg"
                http_response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return http_response
            else:
                raise Http404(f"Could not download photo from S3 (status: {response.status_code})")
                
        except requests.RequestException as e:
            print(f"Error downloading photo from S3: {e}")
            raise Http404("Error accessing photo file from S3")
    
    raise Http404("Photo has no image file")


def download_album(request, slug, quality='optimized'):
    """Download pre-generated album ZIP file."""
    # Check album permissions
    if request.user.is_authenticated and request.user.is_staff:
        album = get_object_or_404(PhotoAlbum, slug=slug)
    else:
        album = get_object_or_404(PhotoAlbum, slug=slug, is_private=False)
    
    # Check if downloads are allowed
    if not album.allow_downloads:
        raise Http404("Downloads are not allowed for this album")
    
    # Determine which quality to download
    if quality not in ['original', 'optimized']:
        quality = 'optimized'
    
    # Get the appropriate zip file
    if quality == 'original':
        zip_file = album.zip_file
    else:
        zip_file = album.zip_file_optimized
    
    # Check if zip file exists
    if not zip_file:
        # Trigger generation if file doesn't exist
        from photos.tasks import generate_album_zip
        generate_album_zip.delay(album.pk)
        
        # Return a message to the user
        raise Http404("The download file is being generated. Please try again in a few moments.")
    
    # Redirect to the secure S3 URL
    # The URL will be pre-signed with expiration time
    try:
        download_url = zip_file.url
        return redirect(download_url)
    except Exception as e:
        print(f"Error getting download URL: {e}")
        raise Http404("Error accessing the download file")


def album_download_status(request, slug):
    """Check the status of album download files (AJAX endpoint)."""
    # Check album permissions
    if request.user.is_authenticated and request.user.is_staff:
        album = get_object_or_404(PhotoAlbum, slug=slug)
    else:
        album = get_object_or_404(PhotoAlbum, slug=slug, is_private=False)
    
    # Check if downloads are allowed
    if not album.allow_downloads:
        return JsonResponse({'error': 'Downloads not allowed'}, status=403)
    
    # Check status of zip files
    status = {
        'album_title': album.title,
        'photo_count': album.photos.count(),
        'downloads_allowed': album.allow_downloads,
        'original': {
            'ready': bool(album.zip_file),
            'size': album.zip_file.size if album.zip_file else None,
            'url': None  # Don't expose URL in status check
        },
        'optimized': {
            'ready': bool(album.zip_file_optimized),
            'size': album.zip_file_optimized.size if album.zip_file_optimized else None,
            'url': None  # Don't expose URL in status check
        }
    }
    
    # If neither file exists, trigger generation
    if not status['original']['ready'] and not status['optimized']['ready']:
        from photos.tasks import generate_album_zip
        generate_album_zip.delay(album.pk)
        status['generation_triggered'] = True
    
    return JsonResponse(status)
