"""URL map for the accounts app (mounted under /accounts/).

Just the HTML login/logout pages (Django's built-in views, pointed at
our templates). The React app does not use these — it signs in through
InsForge (see frontend/src/insforge.js). Google sign-in used to live
here via django-allauth; the InsForge swap (Phase 5) removed it.
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.DemoLoginView.as_view(), name="login"),
    path("logout/", views.DemoLogoutView.as_view(), name="logout"),
]
