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
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from applications.models import Application, GapTask
from resumes.extract import extract_text
from resumes.forms import ResumeUploadForm
from resumes.models import Resume
from resumes.scoring import compute_ats, segment_sections


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


# ---------------------------------------------------------------------------
# Resumes (slice B)
# ---------------------------------------------------------------------------

def _resume_list_json(resume):
    return {
        "id": resume.id,
        "original_name": resume.original_name,
        "ats_score": resume.ats_score,
        "created_at": resume.created_at.isoformat(),
    }


def _resume_detail_json(resume):
    data = _resume_list_json(resume)
    data["breakdown"] = resume.breakdown
    data["extracted_text"] = resume.extracted_text
    return data


def resume_list(request):
    """The signed-in user's resumes, newest first — the React list page."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    resumes = Resume.objects.filter(owner=request.user)
    return JsonResponse({
        "resumes": [_resume_list_json(r) for r in resumes],
    })


@require_POST
def resume_upload(request):
    """Upload a resume file, score it, save it — the same steps as the
    HTML upload view (resumes/views.py), but answering JSON.
    MULTIPART, NOT JSON: a file cannot travel inside a JSON body, so
    the React client sends FormData and the file arrives in
    request.FILES. Validation reuses ResumeUploadForm, so the rules
    (PDF/DOCX only) are identical to the HTML page. One deliberate
    difference: a corrupt file that the HTML view would crash on
    (HTTP 500) answers 400 here, because an API client needs an error
    it can show, not a stack trace."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    form = ResumeUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        errors = form.errors.get("file", ["Invalid file."])
        return JsonResponse({"detail": errors[0]}, status=400)
    uploaded = form.cleaned_data["file"]
    try:
        text = extract_text(uploaded, uploaded.name)
    except Exception:
        # Extraction only: corrupt PDFs/DOCXs land here. Scoring and
        # saving keep their normal errors, so real bugs still surface.
        return JsonResponse(
            {"detail": "Could not read that file. It may be corrupt — "
                       "try re-exporting it as PDF or DOCX."},
            status=400)
    sections = segment_sections(text)
    result = compute_ats(sections, text)
    resume = Resume.objects.create(
        owner=request.user,
        file=uploaded,
        original_name=uploaded.name,
        extracted_text=text,
        ats_score=result["score"],
        breakdown=result,
    )
    return JsonResponse(_resume_detail_json(resume), status=201)


def resume_detail(request, pk):
    """One resume with its full ATS breakdown. Owner-only like the HTML
    result page — another user's id answers 404, and the body is JSON
    (get_object_or_404 would return Django's HTML 404 page)."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    try:
        resume = Resume.objects.get(pk=pk, owner=request.user)
    except Resume.DoesNotExist:
        return JsonResponse({"detail": "Not found."}, status=404)
    return JsonResponse(_resume_detail_json(resume))
