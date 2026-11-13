"""Initial migration for the api app: the InsForge identity link."""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InsforgeIdentity",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sub",
                    models.CharField(
                        help_text="InsForge user id (the JWT 'sub' claim).",
                        max_length=255,
                        unique=True,
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True,
                        help_text="Email from the InsForge token, copied at link time.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=models.CASCADE,
                        related_name="insforge_identity",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
