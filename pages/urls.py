from django.urls import path

from pages.decorators import track_page_visit

from .views import home, robotstxt, health_check

urlpatterns = [
    path("", track_page_visit(home), name="home"),
    path("robots.txt", track_page_visit(robotstxt), name="robotstxt"),
    path("health/", health_check, name="health_check"),
]