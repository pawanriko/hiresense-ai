"""URL map for the React JSON API. All paths live under /api/."""

from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.csrf, name="api-csrf"),
    path("auth/me/", views.me, name="api-me"),
    path("auth/login/", views.login_view, name="api-login"),
    path("auth/logout/", views.logout_view, name="api-logout"),
    path("dashboard/", views.dashboard, name="api-dashboard"),
    path("resumes/", views.resume_list, name="api-resume-list"),
    path("resumes/upload/", views.resume_upload, name="api-resume-upload"),
    path("resumes/<int:pk>/", views.resume_detail, name="api-resume-detail"),
]
