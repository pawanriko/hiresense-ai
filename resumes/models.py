"""Database models for the resumes app.

WHAT A MODEL IS: a Python class that Django turns into a database table.
Each field becomes a column. You never write SQL for basic work — you use
the model (``Resume.objects.create(...)``), and Django handles the SQL.
``makemigrations`` + ``migrate`` create/upgrade the table from this file.

FIELDS:
- owner: which user uploaded this. ForeignKey = "belongs to one user";
  CASCADE means deleting the user deletes their resumes too.
- file: the uploaded file itself, stored under media/resumes/.
- original_name: the filename as uploaded (for display).
- extracted_text: the text pulled out of the file at upload time, so we
  never re-parse the file just to show a score breakdown.
- ats_score: the computed ATS number (0-100), or None if not scored yet.
- breakdown: the full category/check detail from compute_ats, stored as
  JSON so the result page can show every check without recomputing.
- created_at: set automatically when the row is created.
"""

from django.conf import settings
from django.db import models


class Resume(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resumes",
    )
    file = models.FileField(upload_to="resumes/")
    original_name = models.CharField(max_length=255)
    extracted_text = models.TextField(blank=True)
    ats_score = models.IntegerField(null=True, blank=True)
    breakdown = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # newest first, everywhere, by default

    def __str__(self):
        return f"{self.original_name} ({self.ats_score})"
