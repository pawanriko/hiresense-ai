"""Project URL map — the front door of the site.

HOW IT WORKS: Django reads this list top to bottom and hands each request to
the first pattern that matches. ``include()`` hands a whole URL prefix to an
app's own urls.py, so each app owns its little corner of the site:

    /                    -> dashboard app (home page)
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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    # OUR accounts URLs FIRST: they own /accounts/login/ and /logout/,
    # and the Google guard paths. allauth's URLs come second and supply
    # everything else (provider login/callback names, socialaccount
    # helpers). See accounts/urls.py for why this order matters.
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('resumes/', include('resumes.urls')),
    path('jd-match/', include('jdmatch.urls')),
    path('interview/', include('interview.urls')),
    path('applications/', include('applications.urls')),
    path('api/', include('api.urls')),
]
