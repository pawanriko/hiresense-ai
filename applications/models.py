"""Database models for the applications app (slice 4).

WHAT THIS APP STORES — two tables, mirroring the original app's
``applications`` and ``prep_tasks`` rows:

- Application: one job application being tracked. Fields match the
  original exactly: company and role (both required), status (one of the
  original's four pipeline stages), notes, and an optional link to a
  JobDescription. ``updated_at`` refreshes on every save, and the list
  orders by it, newest first — the original lists "recently updated
  first", so touching a row (e.g. changing its status) moves it to the
  top. That is why ``updated_at`` uses ``auto_now`` (set on every save)
  while ``created_at`` uses ``auto_now_add`` (set once, at creation).
- GapTask: one checklist item. Fields match the original: title (max 200
  characters, enforced by the model and the form), source_gap (the fix
  action or weakest-area note behind the task, may be empty for manual
  tasks), and status (todo / doing / done — the original's three states).
  Two optional links record WHERE a task came from: ``analysis`` (a JD
  Match result whose gap was pushed) or ``interview_session`` (a mock
  interview whose weakest area was pushed). Manual tasks have neither
  link. These links are also what duplicate prevention checks: pushing
  the same gap twice must not create a second identical task.

Both models carry ``owner`` (a ForeignKey to the user) so every query
can filter by the signed-in user — that is what makes pages owner-only.
"""

from django.conf import settings
from django.db import models

from interview.models import InterviewSession
from jdmatch.models import JobDescription, MatchAnalysis


class Application(models.Model):
    """One tracked job application."""

    # The original's pipeline stages, verbatim — no invented statuses.
    STATUS_APPLIED = "Applied"
    STATUS_INTERVIEW = "Interview"
    STATUS_OFFER = "Offer"
    STATUS_REJECTED = "Rejected"
    STATUS_CHOICES = [
        (STATUS_APPLIED, "Applied"),
        (STATUS_INTERVIEW, "Interview"),
        (STATUS_OFFER, "Offer"),
        (STATUS_REJECTED, "Rejected"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    company = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_APPLIED
    )
    notes = models.TextField(blank=True)
    # Optional link to a JD the user pasted (the original stores jd_id).
    jd = models.ForeignKey(
        JobDescription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Recently updated first, exactly like the original's list.
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.role} at {self.company} ({self.status})"


class GapTask(models.Model):
    """One prep checklist item, from a gap, a weakest area, or manual."""

    # The original's three task states, verbatim.
    STATUS_TODO = "todo"
    STATUS_DOING = "doing"
    STATUS_DONE = "done"
    STATUS_CHOICES = [
        (STATUS_TODO, "To do"),
        (STATUS_DOING, "Doing"),
        (STATUS_DONE, "Done"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gap_tasks",
    )
    # The original slices titles at 200 characters on insert.
    title = models.CharField(max_length=200)
    # The fix action (JD gap) or weakest-area note (interview), or empty
    # for a task the user typed by hand.
    source_gap = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_TODO
    )
    # Where this task came from, if anywhere. Used by duplicate prevention:
    # a second push of the same gap/area finds the existing task instead
    # of creating a copy.
    analysis = models.ForeignKey(
        MatchAnalysis,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="gap_tasks",
    )
    interview_session = models.ForeignKey(
        InterviewSession,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="gap_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # newest first, like the original

    def __str__(self):
        return self.title

    @property
    def is_done(self):
        """The dashboard's "open" count treats anything not done as open,
        matching the original (open = status != done)."""
        return self.status == self.STATUS_DONE
