from django.urls import path
from . import views

app_name = 'lighthouse_monitor'

urlpatterns = [
    path('api/lighthouse/badge/', views.badge_endpoint, name='badge_endpoint'),
    path('lighthouse/history/', views.history_page, name='history'),
]

