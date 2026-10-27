"""Admin registration for the interview app (slice 3).

WHAT: registering a model here makes it editable at /admin/ — handy for
inspecting a session's transcript while debugging, nothing more.
"""

from django.contrib import admin

from .models import InterviewSession


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ("owner", "track", "difficulty", "status", "overall_score", "created_at")
    list_filter = ("track", "difficulty", "status")
