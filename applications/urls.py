"""URL map for the applications app (mounted under /applications/).

``app_name`` creates a namespace, so templates reverse these by name —
"applications:index", "applications:detail", "applications:tasks" —
instead of hardcoding paths.
"""

from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:pk>/", views.detail, name="detail"),
    path("tasks/", views.tasks, name="tasks"),
    path(
        "tasks/push-from-analysis/<int:pk>/",
        views.push_from_analysis,
        name="push_from_analysis",
    ),
    path(
        "tasks/push-from-interview/<int:pk>/",
        views.push_from_interview,
        name="push_from_interview",
    ),
]
