from django.contrib import admin
from django.utils.html import format_html

from .models import CrawlConfig, CrawlJob


@admin.register(CrawlJob)
class CrawlJobAdmin(admin.ModelAdmin):
    list_display = ("id", "platform", "status_badge", "triggered_by",
                    "contest_count", "participation_count", "cheater_badge",
                    "duration_display", "created_at")
    list_filter = ("platform", "status")
    search_fields = ("celery_task_id", "error_message")
    readonly_fields = ("celery_task_id", "started_at", "finished_at",
                       "contest_count", "participation_count", "cheater_count",
                       "error_message", "log")
    date_hierarchy = "created_at"

    @admin.display(description="状态")
    def status_badge(self, obj):
        colors = {
            CrawlJob.Status.SUCCESS: "#27ae60",
            CrawlJob.Status.FAILED: "#c0392b",
            CrawlJob.Status.PARTIAL: "#e67e22",
            CrawlJob.Status.RUNNING: "#2980b9",
        }
        return format_html('<span style="color:{}">{}</span>',
                           colors.get(obj.status, "#7f8c8d"),
                           obj.get_status_display())

    @admin.display(description="排除作弊")
    def cheater_badge(self, obj):
        return obj.cheater_count or "-"

    @admin.display(description="耗时")
    def duration_display(self, obj):
        d = obj.duration_seconds
        return f"{d:.1f}s" if d is not None else "-"


@admin.register(CrawlConfig)
class CrawlConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "enabled", "cf_count", "atcoder_count",
                    "nowcoder_months_back", "auto_crawl_hour", "updated_at")
