"""Views for the applications app (slice 4).

THREE PAGES, mirroring the original's tracker + Prep Dashboard:

1. index — the tracker: a create form, status counts (Applied / Interview
   / Offer / Rejected, exactly the original dashboard's counts), and the
   list, recently updated first. A per-row status dropdown changes a
   row's status in place; the detail page edits everything else.
2. detail — one application: edit form (company, role, status, notes,
   JD link) + delete button. The original's PATCH only moves status and
   notes, but a tracker that cannot fix a typo'd company name is useless,
   so the edit form covers all fields while keeping the original's
   rules (company/role required, status from the four stages).
3. tasks — the gap-task checklist: manual create form, filter links
   (open / done / all), a done/undone toggle, and a status dropdown
   (todo / doing / done, the original's three states). "Open" means
   status != done, exactly like the original dashboard's open count.

PUSHING GAPS (the point of the checklist): two POST-only helpers turn
report findings into tasks, with duplicate prevention:
- push_from_analysis: for each gap of a JD Match analysis, a task titled
  "Close gap: <criterion>" with the gap's fix action as source_gap —
  the original's exact title/action pair. A gap whose title already
  exists for this analysis is skipped (the original skips titles already
  present for that analysis).
- push_from_interview: for each weakest area of a completed interview
  report, a task titled "Practise interview topic: <area>" with the
  original's exact source note ("Weakest area in your <track> mock
  interview. Rehearse 2 answers on this topic and re-run a session.").
  A title already pushed for this session is skipped. The original
  re-posts interview tasks blindly; skipping duplicates here is the
  task's stated rule and strictly safer (a second click must not spam
  the checklist).

OWNER-ONLY: every object lookup filters by owner=request.user, so
another user's id gives a 404 — the same pattern as slices 1–3.
Every POST ends in a redirect (POST-redirect-GET), so refreshing a page
never resubmits a form.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from interview.models import InterviewSession
from jdmatch.models import MatchAnalysis

from .forms import ApplicationForm, GapTaskForm
from .models import Application, GapTask


def push_analysis_gaps(user, analysis):
    """Create one task per gap of an analysis, skipping duplicates.

    Returns how many tasks were actually created. A gap counts as a
    duplicate when this user already has a task with the same title
    linked to this analysis — the original's skip rule, keyed on title
    per analysis.
    """
    created = 0
    for gap in analysis.gaps or []:
        title = f"Close gap: {gap['criterion']}"
        if GapTask.objects.filter(
            owner=user, analysis=analysis, title=title
        ).exists():
            continue
        GapTask.objects.create(
            owner=user,
            title=title,
            source_gap=gap.get("suggested_action", ""),
            analysis=analysis,
        )
        created += 1
    return created


def push_interview_areas(user, session):
    """Create one task per weakest area of a completed interview report.

    Returns how many tasks were actually created. A weakest area counts
    as a duplicate when this user already has a task with the same title
    linked to this session. An in-progress session has no report yet, so
    pushing it creates nothing (0) instead of crashing.
    """
    created = 0
    for area in (session.report or {}).get("weakest_areas", []):
        title = f"Practise interview topic: {area}"
        if GapTask.objects.filter(
            owner=user, interview_session=session, title=title
        ).exists():
            continue
        GapTask.objects.create(
            owner=user,
            title=title,
            source_gap=(
                f"Weakest area in your {session.track} mock interview. "
                "Rehearse 2 answers on this topic and re-run a session."
            ),
            interview_session=session,
        )
        created += 1
    return created


def _status_counts(user):
    """How many applications per pipeline stage — the dashboard's counts."""
    counts = {}
    for status, _label in Application.STATUS_CHOICES:
        counts[status] = Application.objects.filter(
            owner=user, status=status
        ).count()
    return counts


@login_required
def index(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            form = ApplicationForm(request.POST, user=request.user)
            if form.is_valid():
                application = form.save(commit=False)
                application.owner = request.user
                application.save()
                return redirect("applications:index")
        elif action == "set_status":
            # Per-row status dropdown: only the status changes, and only
            # if the new value is one of the four stages — anything else
            # is ignored rather than saved (never trust a crafted POST).
            application = get_object_or_404(
                Application,
                pk=request.POST.get("application_id"),
                owner=request.user,
            )
            new_status = request.POST.get("status")
            if new_status in dict(Application.STATUS_CHOICES):
                application.status = new_status
                application.save()  # auto_now bumps updated_at, reordering
            return redirect("applications:index")
    else:
        form = ApplicationForm(user=request.user)
    return render(request, "applications/index.html", {
        "form": form,
        "applications": Application.objects.filter(owner=request.user),
        "counts": _status_counts(request.user),
        "statuses": [s for s, _l in Application.STATUS_CHOICES],
    })


@login_required
def detail(request, pk):
    application = get_object_or_404(
        Application, pk=pk, owner=request.user
    )
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "delete":
            application.delete()
            return redirect("applications:index")
        if action == "save":
            form = ApplicationForm(
                request.POST, instance=application, user=request.user
            )
            if form.is_valid():
                form.save()
                return redirect("applications:detail", pk=application.pk)
    else:
        form = ApplicationForm(instance=application, user=request.user)
    return render(request, "applications/detail.html", {
        "form": form,
        "application": application,
    })


@login_required
def tasks(request):
    # Filter: open = anything not done (the original dashboard's rule),
    # done = finished only, all = everything. Default is all, matching
    # the original task list, which shows every task newest first.
    task_filter = request.GET.get("filter", "all")
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            form = GapTaskForm(request.POST)
            if form.is_valid():
                GapTask.objects.create(
                    owner=request.user,
                    title=form.cleaned_data["title"],
                    source_gap=form.cleaned_data["source_gap"],
                )
                return redirect("applications:tasks")
        elif action == "toggle":
            # Done/undone checkbox: done -> back to todo, anything else
            # -> done. ("Doing" tasks toggle to done, like a checkbox.)
            task = get_object_or_404(
                GapTask, pk=request.POST.get("task_id"), owner=request.user
            )
            task.status = (
                GapTask.STATUS_TODO
                if task.status == GapTask.STATUS_DONE
                else GapTask.STATUS_DONE
            )
            task.save()
            return redirect("applications:tasks")
        elif action == "set_status":
            task = get_object_or_404(
                GapTask, pk=request.POST.get("task_id"), owner=request.user
            )
            new_status = request.POST.get("status")
            if new_status in dict(GapTask.STATUS_CHOICES):
                task.status = new_status
                task.save()
            return redirect("applications:tasks")
    else:
        form = GapTaskForm()
    all_tasks = GapTask.objects.filter(owner=request.user)
    if task_filter == "open":
        shown = all_tasks.exclude(status=GapTask.STATUS_DONE)
    elif task_filter == "done":
        shown = all_tasks.filter(status=GapTask.STATUS_DONE)
    else:
        task_filter = "all"
        shown = all_tasks
    return render(request, "applications/tasks.html", {
        "form": form,
        "tasks": shown,
        "filter": task_filter,
        "statuses": [s for s, _l in GapTask.STATUS_CHOICES],
        "open_count": all_tasks.exclude(status=GapTask.STATUS_DONE).count(),
        "done_count": all_tasks.filter(status=GapTask.STATUS_DONE).count(),
    })


@login_required
def push_from_analysis(request, pk):
    """POST-only: push one analysis's gaps onto the checklist, then show
    the task list (new tasks land on top, newest first)."""
    analysis = get_object_or_404(
        MatchAnalysis, pk=pk, owner=request.user
    )
    if request.method == "POST":
        push_analysis_gaps(request.user, analysis)
    return redirect("applications:tasks")


@login_required
def push_from_interview(request, pk):
    """POST-only: push a completed session's weakest areas as tasks."""
    session = get_object_or_404(
        InterviewSession, pk=pk, owner=request.user
    )
    if request.method == "POST":
        push_interview_areas(request.user, session)
    return redirect("applications:tasks")
