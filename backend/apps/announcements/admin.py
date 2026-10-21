from django.contrib import admin

from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "pinned", "is_active",
                    "updated_at", "created_at")
    list_filter = ("level", "pinned", "is_active")
    search_fields = ("title", "content")
    ordering = ("-pinned", "-updated_at")
