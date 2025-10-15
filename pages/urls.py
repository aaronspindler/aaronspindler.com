from django.urls import path

from .views import health_check, home, resume, robotstxt

urlpatterns = [
    path("", home, name="home"),
    path("robots.txt", robotstxt, name="robotstxt"),
    path("health/", health_check, name="health_check"),
    path("resume/", resume, name="resume"),
]
