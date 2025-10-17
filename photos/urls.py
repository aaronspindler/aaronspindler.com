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
]
