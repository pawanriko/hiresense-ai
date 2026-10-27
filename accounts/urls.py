"""URL map for the accounts app (mounted under /accounts/).

ORDER MATTERS HERE: config/urls.py includes this file BEFORE allauth's
URLs, and Django uses the first pattern that matches. So:

  * /accounts/login/ and /accounts/logout/ hit OUR views (demo login
    stays the front door; allauth's own login/logout pages are shadowed
    but still exist for reverse() lookups inside allauth).
  * /accounts/google/login/ and /accounts/google/login/callback/ hit the
    GUARD views in views.py, which delegate to allauth when Google is
    configured and redirect to our login page when it is not. Without
    the guards, an unconfigured visit to those URLs would crash inside
    allauth (no Google app to look up).

The guard paths are deliberately UNNAMED: allauth's own URL names
("google_login", "google_callback") must keep resolving to allauth's
patterns, which is what {% provider_login_url %} and allauth's internals
reverse.
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.DemoLoginView.as_view(), name="login"),
    path("logout/", views.DemoLogoutView.as_view(), name="logout"),
    # Google OAuth guards (see views._google_guard). Unnamed on purpose.
    path("google/login/", views.google_login_guard),
    path("google/login/callback/", views.google_callback_guard),
]
