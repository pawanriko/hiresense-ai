"""Register the Resume model with Django's automatic admin site.

WHAT THE ADMIN IS: a free back-office UI Django builds from your models
(/admin/). Log in with a superuser (see README) to browse, inspect, and
delete uploaded resumes without writing any code. Handy while learning.
"""

from django.contrib import admin

from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("original_name", "owner", "ats_score", "created_at")
    list_filter = ("created_at",)
    search_fields = ("original_name", "owner__username")
    readonly_fields = ("extracted_text",)
