"""Models for the api app.

The api app owns no product data — resumes, JDs, interviews and
applications live in their own apps. The one row it owns is the link
between a Django user and their InsForge identity (Phase 1 of the
InsForge auth swap). Keeping the link in its own table, instead of a
custom user model, is what makes the swap a small change: every
``owner`` foreign key in the project keeps pointing at Django's stock
User, and this table only says "this Django user IS that InsForge
user".
"""

from django.conf import settings
from django.db import models


class InsforgeIdentity(models.Model):
    """One row per Django user that has signed in via InsForge.

    ``sub`` is the InsForge user id — the ``sub`` claim of the JWT.
    It is the stable anchor: emails can change, the sub cannot.
    ``email`` is a copy of the token's email at link time, kept for
    the migration report (see link_insforge_users); the live email
    always comes from the token.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="insforge_identity",
    )
    sub = models.CharField(
        max_length=255,
        unique=True,
        help_text="InsForge user id (the JWT 'sub' claim).",
    )
    email = models.EmailField(
        blank=True,
        help_text="Email from the InsForge token, copied at link time.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} <-> {self.sub}"
