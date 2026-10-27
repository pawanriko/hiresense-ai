"""Database models for the jdmatch app (slice 2).

WHAT THIS APP STORES — two tables, mirroring the original app's
``job_descriptions`` and ``match_analyses`` rows:

- JobDescription: a pasted job description plus its match criteria. The
  criteria live in a JSONField as a list of dicts, exactly the shape the
  scorer in ``resumes/scoring.py`` expects:
  ``{"name": ..., "category": ..., "weight": ..., "required": ...}``.
  JSONField is the right call here because criteria are a small, schemaless
  list that the user edits as a whole — a separate Criteria table would
  add joins without adding value.
- MatchAnalysis: one saved scoring run — which resume, which JD, the
  overall score, the per-criterion results (with evidence quotes), and
  the gaps (with fix actions). Stored as JSON for the same reason: the
  result page shows them verbatim, never recomputes them.

Both models carry ``owner`` (a ForeignKey to the user) so every query can
filter by the signed-in user — that is what makes pages owner-only.
"""

from django.conf import settings
from django.db import models

from resumes.models import Resume


class JobDescription(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_descriptions",
    )
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True)
    raw_text = models.TextField(
        help_text="The full job description text, as pasted by the user."
    )
    # Drafted by extract_criteria_heuristic on save, then edited by the user.
    criteria = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # newest first, everywhere, by default

    def __str__(self):
        return self.title


class MatchAnalysis(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="match_analyses",
    )
    resume = models.ForeignKey(
        Resume, on_delete=models.CASCADE, related_name="match_analyses"
    )
    jd = models.ForeignKey(
        JobDescription, on_delete=models.CASCADE, related_name="match_analyses"
    )
    match_score = models.FloatField()
    criteria_results = models.JSONField(default=list, blank=True)
    gaps = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # newest first, everywhere, by default

    def __str__(self):
        return f"{self.jd.title} — {self.match_score}/100"
