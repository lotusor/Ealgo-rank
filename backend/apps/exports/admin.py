"""导出任务的后台只读展示。

与 `accounts.admin` 的 HandleAudit 同一取舍：留痕表只读，不允许在 admin 里
补录或改写——能改的审计等于没有审计。
"""
from django.contrib import admin

from apps.exports.models import ExportAuditLog, ExportJob


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ("id", "actor", "scope_kind", "year", "layout", "status",
                    "row_count", "download_count", "created_at", "expires_at")
    list_filter = ("status", "scope_kind", "layout", "year", "suspicious")
    search_fields = ("actor__username", "file_name")
    readonly_fields = [f.name for f in ExportJob._meta.fields]
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ExportAuditLog)
class ExportAuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "actor_username", "reason",
                    "job_id_snapshot", "ip", "created_at")
    list_filter = ("event", "reason")
    search_fields = ("actor_username", "ip")
    readonly_fields = [f.name for f in ExportAuditLog._meta.fields]
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
