from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404
from .models import PhotoAlbum, Photo
from pages.decorators import track_page_visit
import os
import zipfile
import tempfile


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


def download_album(request, slug):
    """Download all photos in an album as a ZIP file."""
    # Check album permissions
    if request.user.is_authenticated and request.user.is_staff:
        album = get_object_or_404(PhotoAlbum, slug=slug)
    else:
        album = get_object_or_404(PhotoAlbum, slug=slug, is_private=False)
    
    # Check if downloads are allowed
    if not album.allow_downloads:
        raise Http404("Downloads are not allowed for this album")
    
    photos = album.photos.all()
    
    if not photos:
        raise Http404("No photos in this album")
    
    import requests
    
    # Create a temporary ZIP file
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            added_count = 0
            for index, photo in enumerate(photos):
                if photo.image and hasattr(photo.image, 'url'):
                    try:
                        # Determine filename
                        if photo.original_filename:
                            name, ext = os.path.splitext(photo.original_filename)
                            filename = f"{index+1:03d}_{name}{ext}"
                        elif photo.title:
                            filename = f"{index+1:03d}_{photo.title}.jpg"
                        else:
                            filename = f"{index+1:03d}_photo_{photo.id}.jpg"
                        
                        # Sanitize filename
                        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()
                        
                        # Download from S3 and add to zip
                        url = photo.image.url
                        response = requests.get(url)
                        if response.status_code == 200:
                            zip_file.writestr(filename, response.content)
                            added_count += 1
                            print(f"Added S3 file to zip: {filename}")
                        else:
                            print(f"Failed to download photo {photo.id} from S3: status {response.status_code}")
                            
                    except Exception as e:
                        print(f"Error adding photo {photo.id} to zip: {e}")
                        continue  # Skip photos that can't be added
        
        print(f"Total photos added to ZIP: {added_count}")
        
        if added_count == 0:
            raise Http404("Could not add any photos to the ZIP file")
        
        # Serve the ZIP file
        with open(temp_zip.name, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
        
        album_filename = f"{album.slug}_photos.zip"
        response['Content-Disposition'] = f'attachment; filename="{album_filename}"'
        
        return response
    except Exception as e:
        print(f"Error creating ZIP: {e}")
        raise
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_zip.name)
        except:
            pass
