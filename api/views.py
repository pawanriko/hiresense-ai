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
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from applications.models import Application, GapTask
from applications.views import push_analysis_gaps, push_interview_areas
from interview.models import InterviewSession
from jdmatch.models import JobDescription, MatchAnalysis
from resumes.ai_provider import extract_criteria as ai_extract_criteria
from resumes.ai_provider import (
    interview_questions as ai_interview_questions,
)
from resumes.ai_provider import is_ai_configured
from resumes.ai_provider import score_answer as ai_score_answer
from resumes.extract import extract_text
from resumes.forms import ResumeUploadForm
from resumes.interview import (
    TRACKS,
    build_report,
    pick_questions,
    score_answer_checklist,
    topic_keywords,
)
from resumes.models import Resume
from resumes.scoring import (
    compute_ats,
    extract_criteria_heuristic,
    score_resume,
    segment_sections,
)


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
        # Slice C needs this: the JD-match run form only offers resumes
        # that actually have extracted text ("parsed"). The list page
        # filters on it client-side instead of a second endpoint.
        "has_text": bool((resume.extracted_text or "").strip()),
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


# ---------------------------------------------------------------------------
# JD Match (slice C)
# ---------------------------------------------------------------------------
# Mirrors the HTML flow in jdmatch/views.py, in three steps:
#   1. Paste a JD -> criteria are drafted (AI first, else heuristic).
#   2. Edit the criteria (save / redraft) BEFORE scoring.
#   3. Run the match against a parsed resume -> a saved analysis.
# Scores stay deterministic: AI drafts criteria only, never scores.

def _draft_criteria(title, company, raw_text):
    """Same draft rule as jdmatch/views.py — duplicated here so the api
    app doesn't import a private helper from another app."""
    if is_ai_configured():
        ai_criteria = ai_extract_criteria(title, company, raw_text)
        if ai_criteria:
            return ai_criteria
    return extract_criteria_heuristic(raw_text)


_CATEGORIES = {"skill", "tool", "language", "education", "soft"}


def _clean_criteria(rows):
    """Validate a criteria list from JSON. Returns (criteria, error).
    Mirrors CriterionForm: blank-name rows are dropped, a named row
    needs an integer weight 0-100, and the category must be valid."""
    if not isinstance(rows, list):
        return None, "Criteria must be a list."
    criteria = []
    for row in rows:
        if not isinstance(row, dict):
            return None, "Each criterion must be an object."
        name = str(row.get("name", "")).strip()
        if not name:
            continue  # blank row, dropped like the HTML formset
        category = row.get("category")
        if category not in _CATEGORIES:
            return None, f"Invalid category: {category!r}."
        weight = row.get("weight")
        if isinstance(weight, bool) or not isinstance(weight, int):
            return None, f"Weight is required for criterion {name!r}."
        if not 0 <= weight <= 100:
            return None, f"Weight for criterion {name!r} must be 0-100."
        criteria.append({
            "name": name,
            "category": category,
            "weight": weight,
            "required": bool(row.get("required", False)),
        })
    return criteria, None


def _jd_list_json(jd):
    return {
        "id": jd.id,
        "title": jd.title,
        "company": jd.company,
        "created_at": jd.created_at.isoformat(),
    }


def _jd_json(jd):
    data = _jd_list_json(jd)
    data["raw_text"] = jd.raw_text
    data["criteria"] = jd.criteria
    return data


def _analysis_list_json(analysis):
    return {
        "id": analysis.id,
        "jd_id": analysis.jd_id,
        "jd_title": analysis.jd.title,
        "resume_id": analysis.resume_id,
        "resume_name": analysis.resume.original_name,
        "match_score": analysis.match_score,
        "created_at": analysis.created_at.isoformat(),
    }


def _analysis_json(analysis):
    data = _analysis_list_json(analysis)
    data["criteria_results"] = analysis.criteria_results
    data["gaps"] = analysis.gaps
    return data


def _get_owned(model, pk, user):
    """Owner-filtered lookup. Returns (object, None) or (None, a 404
    JsonResponse) — the same 'another user's id is a 404' rule as the
    HTML pages, but with a JSON body instead of Django's HTML 404."""
    try:
        return model.objects.get(pk=pk, owner=user), None
    except model.DoesNotExist:
        return None, JsonResponse({"detail": "Not found."}, status=404)


def _json_body(request):
    try:
        body = json.loads(request.body or "{}")
    except ValueError:
        return None, JsonResponse({"detail": "Invalid JSON body"}, status=400)
    if not isinstance(body, dict):
        return None, JsonResponse({"detail": "Invalid JSON body"}, status=400)
    return body, None


@require_http_methods(["GET", "POST"])
def jd_collection(request):
    """GET: the user's JDs, newest first. POST: paste a JD (title +
    30+ character text) and get back the JD with drafted criteria."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    if request.method == "GET":
        jds = JobDescription.objects.filter(owner=request.user)
        return JsonResponse({"jds": [_jd_list_json(j) for j in jds]})
    body, error = _json_body(request)
    if error:
        return error
    title = str(body.get("title", "")).strip()
    raw_text = body.get("raw_text", "")
    company = str(body.get("company", "") or "").strip()
    if not title:
        return JsonResponse({"detail": "A title is required."}, status=400)
    if len(title) > 255 or len(company) > 255:
        return JsonResponse(
            {"detail": "Title or company is too long."}, status=400)
    if not isinstance(raw_text, str) or len(raw_text.strip()) < 30:
        return JsonResponse(
            {"detail": "A job description of at least 30 characters "
                       "is required."},
            status=400)
    jd = JobDescription.objects.create(
        owner=request.user,
        title=title,
        company=company,
        raw_text=raw_text,
        criteria=_draft_criteria(title, company, raw_text),
    )
    return JsonResponse(_jd_json(jd), status=201)


def jd_detail(request, pk):
    if not request.user.is_authenticated:
        return _unauthenticated()
    jd, error = _get_owned(JobDescription, pk, request.user)
    if error:
        return error
    return JsonResponse(_jd_json(jd))


@require_http_methods(["PUT"])
def jd_criteria(request, pk):
    """Replace a JD's criteria with the edited list. The HTML page
    scores only SAVED criteria, never unsaved edits — same rule here:
    save first, then run the match."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    jd, error = _get_owned(JobDescription, pk, request.user)
    if error:
        return error
    body, error = _json_body(request)
    if error:
        return error
    criteria, error = _clean_criteria(body.get("criteria"))
    if error:
        return JsonResponse({"detail": error}, status=400)
    jd.criteria = criteria
    jd.save()
    return JsonResponse(_jd_json(jd))


@require_POST
def jd_redraft(request, pk):
    """Fresh draft from the saved JD text (AI when configured, else
    heuristic). Discards edits, exactly like the HTML redraft button."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    jd, error = _get_owned(JobDescription, pk, request.user)
    if error:
        return error
    jd.criteria = _draft_criteria(jd.title, jd.company, jd.raw_text)
    jd.save()
    return JsonResponse(_jd_json(jd))


@require_http_methods(["GET", "POST"])
def analysis_collection(request):
    """GET: the user's saved analyses, newest first. POST: run a match
    — {jd_id, resume_id} — against the JD's SAVED criteria, and save
    the analysis. The resume must be the user's own and parsed
    (non-empty extracted text), and the JD must have criteria."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    if request.method == "GET":
        analyses = MatchAnalysis.objects.filter(owner=request.user)
        return JsonResponse({
            "analyses": [_analysis_list_json(a) for a in analyses],
        })
    body, error = _json_body(request)
    if error:
        return error
    jd, error = _get_owned(JobDescription, body.get("jd_id"),
                           request.user)
    if error:
        return error
    resume, error = _get_owned(Resume, body.get("resume_id"),
                               request.user)
    if error:
        return error
    if not (resume.extracted_text or "").strip():
        return JsonResponse(
            {"detail": "That resume has no extracted text yet."},
            status=400)
    if not jd.criteria:
        return JsonResponse(
            {"detail": "This JD has no criteria yet. Add criteria first, "
                       "then run the match."},
            status=400)
    sections = segment_sections(resume.extracted_text)
    result = score_resume(sections, jd.criteria)
    analysis = MatchAnalysis.objects.create(
        owner=request.user,
        resume=resume,
        jd=jd,
        match_score=result["match_score"],
        criteria_results=result["criteria_results"],
        gaps=result["gaps"],
    )
    return JsonResponse(_analysis_json(analysis), status=201)


def analysis_detail(request, pk):
    if not request.user.is_authenticated:
        return _unauthenticated()
    analysis, error = _get_owned(MatchAnalysis, pk, request.user)
    if error:
        return error
    return JsonResponse(_analysis_json(analysis))


# ---------------------------------------------------------------------------
# Mock Interview (slice D)
# ---------------------------------------------------------------------------
# Mirrors interview/views.py: start a 5-question session (AI questions
# when configured, else the deterministic bank), answer one question at
# a time (AI scoring when configured, else the checklist), finish with
# a report. One deliberate difference: answering a completed session
# returns the finished session unchanged (200) instead of the HTML
# page's redirect — an API client needs data, not a redirect target.

_DIFFICULTIES = {"easy", "medium", "hard"}


def _session_list_json(session):
    transcript = session.transcript or []
    answered = sum(1 for i in transcript if i.get("answer") is not None)
    return {
        "id": session.id,
        "track": session.track,
        "difficulty": session.difficulty,
        "company": session.company,
        "question_source": session.question_source,
        "status": session.status,
        "overall_score": session.overall_score,
        "answered_count": answered,
        "total": len(transcript),
        "created_at": session.created_at.isoformat(),
    }


def _session_json(session):
    data = _session_list_json(session)
    transcript = session.transcript or []
    data["transcript"] = transcript
    data["report"] = session.report
    data["current"] = next(
        (i for i in transcript if i.get("answer") is None), None)
    return data


@require_http_methods(["GET", "POST"])
def session_collection(request):
    """GET: the user's sessions, newest first. POST: start a session —
    {track, difficulty, optional company, optional jd_text} — with 5
    questions drafted the same way the HTML page drafts them."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    if request.method == "GET":
        sessions = InterviewSession.objects.filter(owner=request.user)
        return JsonResponse({
            "sessions": [_session_list_json(s) for s in sessions],
        })
    body, error = _json_body(request)
    if error:
        return error
    track = body.get("track")
    difficulty = body.get("difficulty")
    company = str(body.get("company", "") or "").strip()
    jd_text = body.get("jd_text", "") or ""
    if track not in TRACKS:
        return JsonResponse({"detail": f"Invalid track: {track!r}."},
                            status=400)
    if difficulty not in _DIFFICULTIES:
        return JsonResponse(
            {"detail": f"Invalid difficulty: {difficulty!r}."}, status=400)
    if len(company) > 255:
        return JsonResponse({"detail": "Company is too long."}, status=400)
    if not isinstance(jd_text, str):
        return JsonResponse({"detail": "Invalid JD text."}, status=400)
    questions = None
    question_source = "bank"
    if is_ai_configured():
        ai_questions = ai_interview_questions(
            track, difficulty, jd_text, company)
        if ai_questions:
            questions = ai_questions
            question_source = "ai"
    if questions is None:
        questions = pick_questions(track, difficulty)
    transcript = [
        {
            "question": q["question"],
            "topic": q["topic"],
            "answer": None,
            "feedback": None,
            "scores": None,
            "overall": None,
            "source": None,
        }
        for q in questions
    ]
    session = InterviewSession.objects.create(
        owner=request.user,
        track=track,
        difficulty=difficulty,
        company=company,
        question_source=question_source,
        transcript=transcript,
    )
    return JsonResponse(_session_json(session), status=201)


def session_detail(request, pk):
    if not request.user.is_authenticated:
        return _unauthenticated()
    session, error = _get_owned(InterviewSession, pk, request.user)
    if error:
        return error
    return JsonResponse(_session_json(session))


@require_POST
def session_answer(request, pk):
    """Score ONE answer against the current (first unanswered)
    question — AI scoring first when configured, checklist otherwise
    (and checklist again if the AI call fails), exactly like the HTML
    page. If it was the last question, the report is built and the
    session completes."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    session, error = _get_owned(InterviewSession, pk, request.user)
    if error:
        return error
    if session.status != InterviewSession.STATUS_IN_PROGRESS:
        # Completed sessions never change: same rule as the HTML view,
        # which redirects back to the report instead of erroring.
        return JsonResponse(_session_json(session))
    body, error = _json_body(request)
    if error:
        return error
    answer = body.get("answer", "")
    if not isinstance(answer, str) or len(answer.strip()) < 5:
        return JsonResponse(
            {"detail": "Please write an answer of at least a few words."},
            status=400)
    answer = answer.strip()
    transcript = session.transcript
    index = next(
        (i for i, item in enumerate(transcript)
         if item.get("answer") is None),
        None,
    )
    if index is None:
        return JsonResponse(_session_json(session))
    current = transcript[index]
    checked = None
    answer_source = "checklist"
    if is_ai_configured():
        ai_checked = ai_score_answer(current["question"], answer)
        if ai_checked:
            checked = ai_checked
            answer_source = "ai"
    if checked is None:
        checked = score_answer_checklist(
            current["question"], answer, topic_keywords(current["topic"]))
    transcript[index] = {
        **current,
        "answer": answer,
        "feedback": checked["feedback"],
        "scores": {
            "relevance": checked["relevance"],
            "depth": checked["depth"],
            "structure": checked["structure"],
            "confidence": checked["confidence"],
            "conciseness": checked["conciseness"],
        },
        "overall": checked["overall"],
        "source": answer_source,
    }
    session.transcript = transcript
    if all(item.get("answer") is not None for item in transcript):
        answered = [item for item in transcript
                    if item.get("overall") is not None]
        overall_score, report = build_report(answered)
        session.status = InterviewSession.STATUS_COMPLETED
        session.overall_score = overall_score
        session.report = report
    session.save()
    return JsonResponse(_session_json(session))


# ---------------------------------------------------------------------------
# Applications + gap tasks (slice E)
# ---------------------------------------------------------------------------
# Mirrors applications/views.py: tracker (create/edit/delete, status
# counts, recently-updated-first) + checklist (create, status changes,
# open/done/all filters) + pushing gaps from analyses and weakest areas
# from completed interviews, with the same duplicate skipping. The push
# helpers are reused from applications/views.py — they are pure logic,
# not page views — instead of duplicating the title/action rules.

_APP_STATUSES = {"Applied", "Interview", "Offer", "Rejected"}
_TASK_STATUSES = {"todo", "doing", "done"}


def _application_json(app):
    return {
        "id": app.id,
        "company": app.company,
        "role": app.role,
        "status": app.status,
        "notes": app.notes,
        "jd_id": app.jd_id,
        "jd_title": app.jd.title if app.jd else None,
        "created_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat(),
    }


def _task_json(task):
    return {
        "id": task.id,
        "title": task.title,
        "source_gap": task.source_gap,
        "status": task.status,
        "analysis_id": task.analysis_id,
        "interview_session_id": task.interview_session_id,
        "created_at": task.created_at.isoformat(),
    }


def _owned_jd_or_error(user, jd_id):
    """A JD link inside an application form: the JD must be the user's
    own. Unlike a top-level lookup, a bad link here is a validation
    error (400), not a missing resource (404)."""
    try:
        return JobDescription.objects.get(pk=jd_id, owner=user), None
    except JobDescription.DoesNotExist:
        return None, JsonResponse(
            {"detail": "Invalid job description."}, status=400)


@require_http_methods(["GET", "POST"])
def application_collection(request):
    """GET: the user's applications, recently updated first, plus the
    per-stage counts. POST: create one — company and role required,
    status from the four stages, JD link optional and own-only."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    if request.method == "GET":
        apps = Application.objects.filter(owner=request.user)
        counts = {
            status: Application.objects.filter(
                owner=request.user, status=status).count()
            for status, _label in Application.STATUS_CHOICES
        }
        return JsonResponse({
            "applications": [_application_json(a) for a in apps],
            "counts": counts,
        })
    body, error = _json_body(request)
    if error:
        return error
    company = str(body.get("company", "") or "").strip()
    role = str(body.get("role", "") or "").strip()
    status = body.get("status", Application.STATUS_APPLIED)
    notes = body.get("notes", "") or ""
    if not company or not role:
        return JsonResponse(
            {"detail": "Company and role are required."}, status=400)
    if len(company) > 255 or len(role) > 255:
        return JsonResponse(
            {"detail": "Company or role is too long."}, status=400)
    if status not in _APP_STATUSES:
        return JsonResponse({"detail": f"Invalid status: {status!r}."},
                            status=400)
    if not isinstance(notes, str):
        return JsonResponse({"detail": "Invalid notes."}, status=400)
    jd = None
    if body.get("jd_id") is not None:
        jd, error = _owned_jd_or_error(request.user, body["jd_id"])
        if error:
            return error
    app = Application.objects.create(
        owner=request.user, company=company, role=role, status=status,
        notes=notes, jd=jd,
    )
    return JsonResponse(_application_json(app), status=201)


@require_http_methods(["GET", "PUT", "DELETE"])
def application_detail(request, pk):
    """GET one application. PUT edits it — fields you omit keep their
    values, which is how the list page's status dropdown works (it
    sends the whole row with one field changed). DELETE removes it."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    app, error = _get_owned(Application, pk, request.user)
    if error:
        return error
    if request.method == "GET":
        return JsonResponse(_application_json(app))
    if request.method == "DELETE":
        app.delete()
        return HttpResponse(status=204)
    body, error = _json_body(request)
    if error:
        return error
    if "company" in body:
        company = str(body["company"] or "").strip()
        if not company or len(company) > 255:
            return JsonResponse(
                {"detail": "Company is required."}, status=400)
        app.company = company
    if "role" in body:
        role = str(body["role"] or "").strip()
        if not role or len(role) > 255:
            return JsonResponse({"detail": "Role is required."}, status=400)
        app.role = role
    if "status" in body:
        if body["status"] not in _APP_STATUSES:
            return JsonResponse(
                {"detail": f"Invalid status: {body['status']!r}."},
                status=400)
        app.status = body["status"]
    if "notes" in body:
        if not isinstance(body["notes"], str):
            return JsonResponse({"detail": "Invalid notes."}, status=400)
        app.notes = body["notes"]
    if "jd_id" in body:
        if body["jd_id"] is None:
            app.jd = None
        else:
            jd, error = _owned_jd_or_error(request.user, body["jd_id"])
            if error:
                return error
            app.jd = jd
    app.save()  # auto_now bumps updated_at, moving it to the top
    return JsonResponse(_application_json(app))


@require_http_methods(["GET", "POST"])
def task_collection(request):
    """GET: the user's tasks, newest first, filtered by ?filter=
    (open = not done, done, all — anything else falls back to all,
    like the HTML page). POST: create a manual task — title required,
    at most 200 characters."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    if request.method == "GET":
        task_filter = request.GET.get("filter", "all")
        all_tasks = GapTask.objects.filter(owner=request.user)
        if task_filter == "open":
            shown = all_tasks.exclude(status=GapTask.STATUS_DONE)
        elif task_filter == "done":
            shown = all_tasks.filter(status=GapTask.STATUS_DONE)
        else:
            task_filter = "all"
            shown = all_tasks
        return JsonResponse({
            "tasks": [_task_json(t) for t in shown],
            "filter": task_filter,
            "open_count": all_tasks.exclude(
                status=GapTask.STATUS_DONE).count(),
            "done_count": all_tasks.filter(
                status=GapTask.STATUS_DONE).count(),
        })
    body, error = _json_body(request)
    if error:
        return error
    title = str(body.get("title", "") or "").strip()
    source_gap = body.get("source_gap", "") or ""
    if not title or len(title) > 200:
        return JsonResponse(
            {"detail": "A task title of 1-200 characters is required."},
            status=400)
    if not isinstance(source_gap, str):
        return JsonResponse({"detail": "Invalid source_gap."}, status=400)
    task = GapTask.objects.create(
        owner=request.user, title=title, source_gap=source_gap)
    return JsonResponse(_task_json(task), status=201)


@require_http_methods(["PUT"])
def task_detail(request, pk):
    """Update a task — status (todo/doing/done), title, or source_gap.
    The list page's done checkbox is just this endpoint with the
    toggled status (done -> todo, anything else -> done, like the
    HTML toggle)."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    task, error = _get_owned(GapTask, pk, request.user)
    if error:
        return error
    body, error = _json_body(request)
    if error:
        return error
    if "status" in body:
        if body["status"] not in _TASK_STATUSES:
            return JsonResponse(
                {"detail": f"Invalid status: {body['status']!r}."},
                status=400)
        task.status = body["status"]
    if "title" in body:
        title = str(body["title"] or "").strip()
        if not title or len(title) > 200:
            return JsonResponse(
                {"detail": "A task title of 1-200 characters is required."},
                status=400)
        task.title = title
    if "source_gap" in body:
        if not isinstance(body["source_gap"], str):
            return JsonResponse({"detail": "Invalid source_gap."},
                                status=400)
        task.source_gap = body["source_gap"]
    task.save()
    return JsonResponse(_task_json(task))


@require_POST
def push_analysis(request, pk):
    """Push one analysis's gaps onto the checklist, skipping
    duplicates. Returns how many tasks were actually created."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    analysis, error = _get_owned(MatchAnalysis, pk, request.user)
    if error:
        return error
    created = push_analysis_gaps(request.user, analysis)
    return JsonResponse({"created": created})


@require_POST
def push_interview(request, pk):
    """Push a completed session's weakest areas onto the checklist,
    skipping duplicates. An in-progress session has no report yet, so
    pushing it creates nothing (0)."""
    if not request.user.is_authenticated:
        return _unauthenticated()
    session, error = _get_owned(InterviewSession, pk, request.user)
    if error:
        return error
    created = push_interview_areas(request.user, session)
    return JsonResponse({"created": created})
