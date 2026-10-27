"""Database models for the interview app (slice 3).

WHAT THIS APP STORES — one table, mirroring the original app's
``mock_sessions`` rows:

- InterviewSession: who owns it, which track/difficulty, whether it is
  still in progress or completed, the overall score (once finished), the
  transcript, and the final report. The transcript and report live in
  JSONFields as lists/dicts of plain data, exactly the shape the original
  app stores: a transcript item is ``{question, topic, answer, feedback,
  scores, overall}`` with ``None`` for the parts not answered yet. JSON
  is the right call here because a session's transcript is one small
  document the page shows verbatim — it is never queried by its inner
  fields, so a separate Answer table would add joins without value.

OWNER-ONLY: every view looks sessions up with
``get_object_or_404(InterviewSession, pk=..., owner=request.user)``, so
another user's id gives a 404 — the same pattern as slices 1–2.
"""

from django.conf import settings
from django.db import models


class InterviewSession(models.Model):
    """One mock-interview run: 5 questions, answered one at a time."""

    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_sessions",
    )
    track = models.CharField(max_length=50)
    difficulty = models.CharField(max_length=20)
    # Company the session targets (optional, from the start form). It is
    # passed to the AI question generator so questions can be grounded
    # in the company as well as the JD; bank sessions leave it blank.
    company = models.CharField(max_length=255, blank=True, default="")
    # Where the session's questions came from: "bank" (deterministic
    # question bank) or "ai" (Groq). Old sessions predate the field and
    # read as "bank", which is what they were.
    question_source = models.CharField(max_length=20, default="bank")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS
    )
    # Null until the last question is answered; then the rounded mean of
    # the per-answer overall scores (see build_report in resumes/interview.py).
    overall_score = models.IntegerField(null=True, blank=True)
    # List of transcript items; unanswered items carry answer/feedback/
    # scores/overall as None, exactly like the original app.
    transcript = models.JSONField(default=list, blank=True)
    # The final report dict (topic_scores, weakest_areas, weakest_question,
    # feedback_source); empty until the session completes.
    report = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # newest first, everywhere, by default

    def __str__(self):
        score = f" — {self.overall_score}/100" if self.overall_score is not None else ""
        return f"{self.track} · {self.difficulty} · {self.status}{score}"

    @property
    def current_item(self):
        """The first unanswered transcript item, or None if all answered."""
        for item in self.transcript:
            if item.get("answer") is None:
                return item
        return None

    @property
    def answered_count(self):
        """How many questions have answers — used for 'Question N of M'."""
        return sum(1 for item in self.transcript if item.get("answer") is not None)

    @property
    def last_answered(self):
        """The most recently answered item, for showing its feedback after
        answering. Transcript order is answer order, so it is the last item
        with a non-None answer."""
        answered = [item for item in self.transcript if item.get("answer") is not None]
        return answered[-1] if answered else None
