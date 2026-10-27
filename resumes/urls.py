"""URL map for the resumes app (mounted under /resumes/ by config/urls.py).

``app_name`` creates a namespace, so templates and views can reverse these
by name — "resumes:upload" and "resumes:result" — instead of hardcoding
paths. If a path ever changes, the names keep working.
"""

from django.urls import path

from . import views

app_name = "resumes"

urlpatterns = [
    path("upload/", views.upload, name="upload"),
    path("<int:pk>/", views.result, name="result"),
]
