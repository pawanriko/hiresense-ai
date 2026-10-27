"""Views for the interview app (slice 3).

THE FLOW, mirroring the original page (start a session, answer one
question at a time, finish with a report):

1. index (GET)  — start form (track + difficulty + optional company
   and JD text) + past sessions, newest first.
   index (POST) — validate the form, then get 5 questions: AI-generated
   from JD + company + track + difficulty when an AI provider is
   configured (resumes/ai_provider.py picks Groq or Gemini), otherwise
   the deterministic bank — and the bank again if the AI call fails.
   The session records which source was used (question_source).
   Transcript items start with answer/feedback/scores/overall/source
   as None; redirect to detail.
2. detail (GET)  — if in progress: the current (first unanswered)
   question + answer form + the feedback from the just-answered question
   (if any) + answers so far. If completed: the overall report.
   detail (POST) — score ONE answer: AI scoring first when an AI
   provider is configured, checklist otherwise (and checklist again if
   the AI call fails). The per-answer source ("ai" or "checklist") is saved on
   the transcript item, and the report's feedback_source derives from
   it. If it was the last question, build the report, mark the session
   completed, and set the overall score. Then redirect (POST-redirect-GET,
   so refreshing never re-submits an answer).

Scores themselves never change meaning between sources: both scorers
use the same rubric weights (30/25/20/15/10) and the same overall
formula. What changes is who writes the feedback — a model, or fixed
rules. Match and ATS scores are a different thing entirely and stay
deterministic always (see resumes/scoring.py).

OWNER-ONLY: every lookup filters by owner=request.user, so another
user's id gives a 404 — the same pattern as slices 1–2. Answering a
completed session changes nothing: the view redirects back to the report
instead of erroring, which is friendlier on the web than the original
API's 409 and just as safe — and keeps every POST ending in a redirect,
so refreshing never re-submits an answer.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from resumes.ai_provider import (
    interview_questions,
    is_ai_configured,
    score_answer,
)
from resumes.interview import (
    build_report,
    pick_questions,
    score_answer_checklist,
    topic_keywords,
)

from .forms import AnswerForm, StartSessionForm
from .models import InterviewSession


@login_required
def index(request):
    if request.method == "POST":
        form = StartSessionForm(request.POST)
        if form.is_valid():
            track = form.cleaned_data["track"]
            difficulty = form.cleaned_data["difficulty"]
            company = form.cleaned_data["company"]
            jd_text = form.cleaned_data["jd_text"]
            # AI questions first when a provider is configured: fresh
            # questions grounded in the JD + company + track +
            # difficulty. Any AI failure (or no key) falls back to the
            # bank — pick_questions is deterministic: same track +
            # difficulty always yields the same 5 questions, in order.
            questions = None
            question_source = "bank"
            if is_ai_configured():
                ai_questions = interview_questions(
                    track, difficulty, jd_text, company
                )
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
            return redirect("interview:detail", pk=session.pk)
    else:
        form = StartSessionForm()
    return render(request, "interview/index.html", {
        "form": form,
        "sessions": InterviewSession.objects.filter(owner=request.user),
    })


@login_required
def detail(request, pk):
    session = get_object_or_404(InterviewSession, pk=pk, owner=request.user)

    if request.method == "POST" and session.status != InterviewSession.STATUS_IN_PROGRESS:
        # Answered already finished: change nothing, redirect to the report.
        return redirect("interview:detail", pk=session.pk)
    if request.method == "POST":
        form = AnswerForm(request.POST)
        if form.is_valid():
            # Find the first unanswered item — answers always land in
            # order, so this is the question currently on screen.
            transcript = session.transcript
            index = next(
                (i for i, item in enumerate(transcript) if item.get("answer") is None),
                None,
            )
            if index is not None:
                current = transcript[index]
                answer = form.cleaned_data["answer"]
                # AI scoring first when a provider is configured, else
                # the checklist — and the checklist again if the AI
                # call fails. Both use the same rubric weights and
                # overall formula; only the feedback author differs,
                # and the per-answer source is saved so the report can
                # say which one wrote each feedback.
                checked = None
                answer_source = "checklist"
                if is_ai_configured():
                    ai_checked = score_answer(current["question"], answer)
                    if ai_checked:
                        checked = ai_checked
                        answer_source = "ai"
                if checked is None:
                    checked = score_answer_checklist(
                        current["question"], answer, topic_keywords(current["topic"])
                    )
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
                    answered = [item for item in transcript if item.get("overall") is not None]
                    overall_score, report = build_report(answered)
                    session.status = InterviewSession.STATUS_COMPLETED
                    session.overall_score = overall_score
                    session.report = report
                session.save()
            return redirect("interview:detail", pk=session.pk)
    else:
        # GET only (POSTs to completed sessions returned early above, and
        # an invalid POST falls through with its bound form showing errors).
        form = AnswerForm()

    return render(request, "interview/detail.html", {
        "session": session,
        "form": form,
        "current": session.current_item,
        "answered_count": session.answered_count,
        "last_answered": session.last_answered,
    })
