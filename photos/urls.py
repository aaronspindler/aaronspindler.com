from django.urls import path

from . import views

app_name = "photos"

urlpatterns = [
    path("album/<slug:slug>/", views.album_detail, name="album_detail"),
    path("photo/<int:pk>/", views.photo_detail, name="photo_detail"),
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
]
