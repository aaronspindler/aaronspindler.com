from django.urls import path

from . import views

app_name = "photos"

urlpatterns = [
    path("album/<slug:slug>/", views.album_detail, name="album_detail"),
    path(
        "album/<slug:slug>/photo/<int:photo_id>/download/",
        views.download_photo,
        name="download_photo",
    ),
    path(
        "album/<slug:slug>/download/",
        views.download_album_zip,
        name="download_album_zip",
    ),
    path(
        "album/<slug:slug>/photo/<int:photo_id>/exif/",
        views.photo_exif_api,
        name="photo_exif_api",
    ),
    # Bulk upload API (UI is in admin)
    path("api/upload/", views.upload_photo_api, name="upload_photo_api"),
    path("api/photo/<int:photo_id>/status/", views.photo_status_api, name="photo_status_api"),
]
