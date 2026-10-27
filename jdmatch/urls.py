"""URL map for the jdmatch app (mounted under /jd-match/ by config/urls.py).

``app_name`` creates a namespace, so templates reverse these by name —
"jdmatch:index", "jdmatch:detail", "jdmatch:result" — instead of
hardcoding paths.
"""

from django.urls import path

from . import views

app_name = "jdmatch"

urlpatterns = [
    path("", views.index, name="index"),
    path("jds/<int:pk>/", views.detail, name="detail"),
    path("analyses/<int:pk>/", views.result, name="result"),
]
