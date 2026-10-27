"""Admin registrations for slice 4 (optional, for /admin/ browsing)."""

from django.contrib import admin

from .models import Application, GapTask


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("company", "role", "status", "owner", "updated_at")
    list_filter = ("status",)


@admin.register(GapTask)
class GapTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "owner", "created_at")
    list_filter = ("status",)
