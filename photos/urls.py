from django.urls import path
from .views import AlbumListView, AlbumDetailView

app_name = 'photos'

urlpatterns = [
    path('', AlbumListView.as_view(), name='album_list'),
    path('albums/<int:pk>/', AlbumDetailView.as_view(), name='album_detail'),
]