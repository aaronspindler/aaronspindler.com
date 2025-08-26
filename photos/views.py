from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import PhotoAlbum, Photo
from pages.decorators import track_page_visit


@track_page_visit 
def album_detail(request, slug):
    album = get_object_or_404(PhotoAlbum, slug=slug)
    photos = album.photos.all().order_by('-date_taken', '-created_at')
    
    return render(request, 'photos/album_detail.html', {
        'album': album,
        'photos': photos
    })
