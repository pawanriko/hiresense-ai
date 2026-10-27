"""Views for the dashboard app — the home page.

WHAT IT DOES: shows the signed-in user's resumes (newest first) and their
latest ATS score at a glance, plus — since slice 4 — the Prep Dashboard
counts from the original: open gap tasks (anything not done), done tasks,
and applications per pipeline stage. Anonymous visitors never get here:
the ``@login_required`` decorator redirects them to the login page first
(see LOGIN_URL in settings).
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from applications.models import Application, GapTask
from resumes.models import Resume


@login_required
def home(request):
    resumes = Resume.objects.filter(owner=request.user)
    latest = resumes.first()  # Meta.ordering is newest-first, so first is latest
    tasks = GapTask.objects.filter(owner=request.user)
    app_counts = {}
    for status, _label in Application.STATUS_CHOICES:
        app_counts[status] = Application.objects.filter(
            owner=request.user, status=status
        ).count()
    return render(request, "dashboard/home.html", {
        "resumes": resumes,
        "latest": latest,
        # "Open" means not done, exactly like the original dashboard.
        "open_tasks": tasks.exclude(status=GapTask.STATUS_DONE).count(),
        "done_tasks": tasks.filter(status=GapTask.STATUS_DONE).count(),
        "app_counts": app_counts,
    })
