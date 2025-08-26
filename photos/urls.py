from django.urls import path
from . import views

app_name = 'photos'

urlpatterns = [
    path('album/<slug:slug>/', views.album_detail, name='album_detail'),
]