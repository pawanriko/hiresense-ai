"""Project URL map — the front door of the site.

HOW IT WORKS: Django reads this list top to bottom and hands each request to
the first pattern that matches. ``include()`` hands a whole URL prefix to an
app's own urls.py, so each app owns its little corner of the site:

    /                    -> React SPA (production) — see SPA_ROUTES below
    /accounts/login/     -> accounts app (Django's built-in login view)
    /accounts/logout/    -> accounts app (logout)
    /accounts/google/login/ (+ callback) -> accounts app guards, which
        delegate to django-allauth's Google flow when configured, or
        redirect to the login page when it is not (see accounts/urls.py)
    /resumes/upload/     -> resumes app (upload a resume)
    /resumes/<id>/       -> resumes app (one scored resume)
    /jd-match/           -> jdmatch app (JD Match: paste JD, edit criteria, run match)
    /jd-match/jds/<id>/  -> jdmatch app (one JD's criteria + run match)
    /jd-match/analyses/<id>/ -> jdmatch app (one saved match result)
    /interview/          -> interview app (Mock Interview: start session, answer, report)
    /interview/<id>/     -> interview app (one session: current question or report)
    /applications/       -> applications app (tracker + gap tasks, slice 4)
    /applications/tasks/ -> applications app (gap-task checklist)
    /api/                -> api app (JSON endpoints for the React frontend)
    /admin/              -> Django's automatic admin site
"""

from django.contrib import admin
from django.urls import include, path

from . import views as config_views

# REACT SPA ROUTES (production): when Django serves the built React app
# (Render), these exact paths return the SPA's index.html so React
# Router takes over. They sit BEFORE the HTML apps' includes on purpose:
#   * '' must beat dashboard's '' — the live homepage IS the React app.
#   * 'resumes' (no slash) must beat the HTML resumes app, or Django's
#     APPEND_SLASH would bounce it to the HTML page instead.
# The HTML pages stay reachable at their trailing-slash URLs
# (/resumes/, /jd-match/, ...) — only the no-slash SPA paths are taken.
SPA_ROUTES = [
    '',
    'login',
    'resumes',
    'resumes/<int:pk>',
    'jd-match',
    'jd-match/<int:pk>',
    'jd-match/analyses/<int:pk>',
    'interview',
    'interview/<int:pk>',
    'applications',
    'applications/tasks',
    'applications/<int:pk>',
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    # OUR accounts URLs FIRST: they own /accounts/login/ and /logout/,
    # and the Google guard paths. allauth's URLs come second and supply
    # everything else (provider login/callback names, socialaccount
    # helpers). See accounts/urls.py for why this order matters.
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    # Root-level files from the built frontend (favicon, icons).
    path('favicon.svg', config_views.site_file, {'name': 'favicon.svg'}),
    path('icons.svg', config_views.site_file, {'name': 'icons.svg'}),
    # The React app itself (production; in dev Vite serves these).
    *[path(route, config_views.spa_index) for route in SPA_ROUTES],
    # HTML pages: the dev interface, still live at trailing-slash URLs.
    path('', include('dashboard.urls')),
    path('resumes/', include('resumes.urls')),
    path('jd-match/', include('jdmatch.urls')),
    path('interview/', include('interview.urls')),
    path('applications/', include('applications.urls')),
]
