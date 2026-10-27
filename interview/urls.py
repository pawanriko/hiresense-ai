"""URL map for the interview app (mounted under /interview/ by config/urls.py).

``app_name`` creates a namespace, so templates reverse these by name —
"interview:index", "interview:detail" — instead of hardcoding paths.
"""

from django.urls import path

from . import views

app_name = "interview"

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:pk>/", views.detail, name="detail"),
]
