"""URL map for the dashboard app (mounted at the site root)."""

from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
]
