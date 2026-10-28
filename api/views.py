"""JSON API views for the React frontend.

AUTH MODEL — session auth, no tokens, no new dependencies:
  * The React dev server (Vite, :5173) proxies /api/* to Django (:8000),
    so from the browser's point of view every API call is same-origin.
    That means no CORS setup and no cookie gymnastics: the session
    cookie and the CSRF cookie just work like a normal Django page.
  * Every POST needs a CSRF token. The frontend first calls
    GET /api/auth/csrf/ (which sets the csrftoken cookie), reads that
    cookie in JS, and sends it back as the X-CSRFToken header.
    Django's CsrfViewMiddleware checks it exactly like a form post.
  * @login_required would redirect anonymous API calls to the HTML
    login page, which React cannot use — so these views check
    request.user.is_authenticated themselves and answer 401 JSON.

WHY NOT DJANGO REST FRAMEWORK: these endpoints are thin wrappers
around queries the HTML views already make (see dashboard/views.py).
JsonResponse + the session framework covers them with zero new
dependencies, which keeps Windows setup as one pip install.
"""

import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from applications.models import Application, GapTask
from resumes.models import Resume


def _unauthenticated():
    return JsonResponse({"detail": "Not authenticated"}, status=401)


@ensure_csrf_cookie
def csrf(request):
    """Set the csrftoken cookie. The frontend calls this once on load."""
    return JsonResponse({})


def me(request):
    """Who is signed in, if anyone. The frontend calls this on load
    to decide between the login page and the app."""
    if request.user.is_authenticated:
        return JsonResponse({
            "authenticated": True,
            "username": request.user.username,
        })
    return JsonResponse({"authenticated": False})


@require_POST
def login_view(request):
    """Sign in with a username + password JSON body, creating the
    same session the HTML login page creates."""
    try:
        body = json.loads(request.body or "{}")
    except ValueError:
        return JsonResponse({"detail": "Invalid JSON body"}, status=400)
    user = authenticate(
        request,
        username=body.get("username", ""),
        password=body.get("password", ""),
    )
    if user is None:
        return JsonResponse(
            {"detail": "Invalid username or password"}, status=400)
    login(request, user)
    return JsonResponse({"username": user.username})


@require_POST
def logout_view(request):
    """Sign out, ending the session."""
    logout(request)
    return JsonResponse({})


def dashboard(request):
    """Dashboard data for the React home page — the same numbers the
    HTML dashboard shows (see dashboard/views.py), as JSON. Only the
    signed-in user's own rows, exactly like the HTML page."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    resumes = Resume.objects.filter(owner=request.user)
    tasks = GapTask.objects.filter(owner=request.user)
    app_counts = {}
    for status, _label in Application.STATUS_CHOICES:
        app_counts[status] = Application.objects.filter(
            owner=request.user, status=status
        ).count()

    def resume_json(resume):
        return {
            "id": resume.id,
            "original_name": resume.original_name,
            "ats_score": resume.ats_score,
            "created_at": resume.created_at.isoformat(),
        }

    latest = resumes.first()  # Meta.ordering is newest-first
    return JsonResponse({
        "resumes": [resume_json(r) for r in resumes],
        "latest": resume_json(latest) if latest else None,
        "open_tasks": tasks.exclude(status=GapTask.STATUS_DONE).count(),
        "done_tasks": tasks.filter(status=GapTask.STATUS_DONE).count(),
        "app_counts": app_counts,
    })
