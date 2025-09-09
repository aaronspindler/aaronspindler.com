from django.urls import path
from .views import (
    ResumeListView,
    ResumeDetailView,
    resume_json_view,
    resume_pdf_view,
    resume_default_view
)

app_name = 'resume'

urlpatterns = [
    path('', resume_default_view, name='default'),
    path('list/', ResumeListView.as_view(), name='list'),
    path('<slug:slug>/', ResumeDetailView.as_view(), name='detail'),
    path('<slug:slug>/json/', resume_json_view, name='json'),
    path('<slug:slug>/pdf/', resume_pdf_view, name='pdf'),
]

