"""Views for the jdmatch app (slice 2).

THE FLOW, mirroring the original page's three sections:

1. index (GET)  — paste-JD form + saved JDs + past analyses (newest first).
   index (POST) — save a JD, draft criteria (AI first when a provider
   is configured, else the heuristic extractor), redirect to the JD
   detail page so the user edits criteria BEFORE scoring.
2. detail (GET)  — criteria formset (edit/delete/add) + run-match form.
   detail (POST) — one of three actions, chosen by a hidden "action" field:
     - "save_criteria": store the edited criteria on the JD.
     - "redraft": replace criteria with a fresh draft (AI when
       configured, else heuristic; edits lost).
     - "run_match": score the picked resume against the SAVED criteria
       (the original scores the approved criteria, not unsaved edits),
       save a MatchAnalysis, redirect to its result page.
3. result (GET)  — the saved analysis: score, per-criterion evidence
   quotes, and gap fix actions. Never recomputed, only displayed.

OWNER-ONLY: every object lookup filters by owner=request.user, so another
user's id gives a 404 — the same pattern as slice 1's resume pages.
"""

from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render

from resumes.ai_provider import extract_criteria, is_ai_configured
from resumes.models import Resume
from resumes.scoring import (
    extract_criteria_heuristic,
    score_resume,
    segment_sections,
)

from .forms import CriterionForm, JobDescriptionForm, RunMatchForm
from .models import JobDescription, MatchAnalysis

# A formset = the same form repeated for a list. extra=1 gives one blank
# "add a criterion" row; can_delete=True adds a delete checkbox per row.
CriterionFormSet = formset_factory(CriterionForm, extra=1, can_delete=True)


def _draft_criteria(title, company, raw_text):
    """Draft criteria for a JD: AI first when a provider is configured
    (Groq or Gemini, per resumes/ai_provider.py), heuristic otherwise
    — and heuristic again if the AI call fails. Either way the result
    is only a DRAFT: the candidate edits it on the detail page before
    any scoring happens, so a weak AI draft costs nothing and a good
    one saves typing."""
    if is_ai_configured():
        ai_criteria = extract_criteria(title, company, raw_text)
        if ai_criteria:
            return ai_criteria
    return extract_criteria_heuristic(raw_text)


def _criteria_to_initial(criteria):
    """Stored criteria dicts -> formset initial data (same keys as the form)."""
    return [
        {
            "name": c["name"],
            "category": c["category"],
            "weight": c["weight"],
            "required": c["required"],
        }
        for c in criteria
    ]


def _formset_to_criteria(formset):
    """Validated formset -> stored criteria dicts. Untouched extra rows
    (empty name) and rows ticked for deletion are skipped, not saved."""
    criteria = []
    for form in formset:
        data = form.cleaned_data
        if data.get("DELETE"):
            continue  # row the user ticked for deletion
        if not data.get("name"):
            continue  # blank "add" row the user left empty
        criteria.append(
            {
                "name": data["name"],
                "category": data["category"],
                "weight": data["weight"],
                "required": data["required"],
            }
        )
    return criteria


def _run_match_form(user):
    """RunMatchForm whose resume dropdown only offers the user's resumes
    that actually have extracted text (the "parsed" filter)."""
    form = RunMatchForm()
    form.fields["resume"].queryset = Resume.objects.filter(
        owner=user
    ).exclude(extracted_text="")
    return form


@login_required
def index(request):
    if request.method == "POST":
        form = JobDescriptionForm(request.POST)
        if form.is_valid():
            # Draft immediately (AI when configured, else heuristic),
            # exactly like the original: the candidate edits this draft
            # before scoring.
            criteria = _draft_criteria(
                form.cleaned_data["title"],
                form.cleaned_data["company"],
                form.cleaned_data["raw_text"],
            )
            jd = JobDescription.objects.create(
                owner=request.user,
                title=form.cleaned_data["title"],
                company=form.cleaned_data["company"],
                raw_text=form.cleaned_data["raw_text"],
                criteria=criteria,
            )
            return redirect("jdmatch:detail", pk=jd.pk)
    else:
        form = JobDescriptionForm()
    return render(request, "jdmatch/index.html", {
        "form": form,
        "jds": JobDescription.objects.filter(owner=request.user),
        "analyses": MatchAnalysis.objects.filter(owner=request.user),
    })


@login_required
def detail(request, pk):
    jd = get_object_or_404(JobDescription, pk=pk, owner=request.user)
    message = None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "redraft":
            # Fresh draft (AI when configured, else heuristic) from the
            # saved JD text. This discards any edits — the page says
            # so, so it is never a surprise.
            jd.criteria = _draft_criteria(jd.title, jd.company, jd.raw_text)
            jd.save()
            return redirect("jdmatch:detail", pk=jd.pk)
        if action == "save_criteria":
            formset = CriterionFormSet(request.POST)
            if formset.is_valid():
                jd.criteria = _formset_to_criteria(formset)
                jd.save()
                return redirect("jdmatch:detail", pk=jd.pk)
        elif action == "run_match":
            form = RunMatchForm(request.POST)
            form.fields["resume"].queryset = Resume.objects.filter(
                owner=request.user
            ).exclude(extracted_text="")
            if form.is_valid():
                if not jd.criteria:
                    # Mirrors the original's no_criteria error: score only
                    # with approved criteria, never with an empty list.
                    message = ("This JD has no criteria yet. "
                               "Add criteria first, then run the match.")
                else:
                    resume = form.cleaned_data["resume"]
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
                    return redirect("jdmatch:result", pk=analysis.pk)
            formset = CriterionFormSet(initial=_criteria_to_initial(jd.criteria))
            return render(request, "jdmatch/detail.html", {
                "jd": jd, "formset": formset, "run_form": form,
                "message": message,
            })
        # Fall through to re-render below for invalid criteria formsets.
        formset = CriterionFormSet(request.POST)
    else:
        formset = CriterionFormSet(initial=_criteria_to_initial(jd.criteria))

    return render(request, "jdmatch/detail.html", {
        "jd": jd,
        "formset": formset,
        "run_form": _run_match_form(request.user),
        "message": message,
    })


@login_required
def result(request, pk):
    # owner=request.user: another user's analysis id gives a 404.
    analysis = get_object_or_404(MatchAnalysis, pk=pk, owner=request.user)
    return render(request, "jdmatch/result.html", {"analysis": analysis})
