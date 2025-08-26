from django.urls import path
from . import views

app_name = 'photos'

urlpatterns = [
    path('album/<slug:slug>/', views.album_detail, name='album_detail'),
    path('album/<slug:slug>/download/', views.download_album, name='download_album'),
    path('album/<slug:slug>/download/<str:quality>/', views.download_album, name='download_album_quality'),
    path('album/<slug:slug>/download-status/', views.album_download_status, name='album_download_status'),
    path('album/<slug:slug>/photo/<int:photo_id>/download/', views.download_photo, name='download_photo'),
]