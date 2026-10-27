"""Admin registrations for the jdmatch app (same pattern as slice 1)."""

from django.contrib import admin

from .models import JobDescription, MatchAnalysis

admin.site.register(JobDescription)
admin.site.register(MatchAnalysis)
