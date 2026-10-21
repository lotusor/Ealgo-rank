from django.contrib import admin, messages
from django.utils import timezone

from apps.accounts.models import UserRole

from .models import (AdminApplicationStatus, AtCoderAffiliationAlias,
                     ScoreRulePage, School,
                     SchoolAdminApplication, ScoreConfig)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "short_name", "code")
    prepopulated_fields = {"code": ("short_name",)}


@admin.register(SchoolAdminApplication)
class SchoolAdminApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "school", "status", "reviewer",
                    "created_at", "reviewed_at")
    list_filter = ("status", "school")
    search_fields = ("applicant__username", "school__name", "reason")
    raw_id_fields = ("applicant", "school", "reviewer")
    readonly_fields = ("created_at", "reviewed_at")
    actions = ["approve", "reject"]

    @admin.action(description="通过申请并授予学校管理员")
    def approve(self, request, queryset):
        qs = queryset.filter(status=AdminApplicationStatus.PENDING)
        n = 0
        for app in qs.select_related("applicant"):
            user = app.applicant
            user.role = UserRole.SCHOOL_ADMIN
            user.school = app.school
            user.school_bound_at = timezone.now()
            user.save(update_fields=["role", "school", "school_bound_at"])
            # 学校确定后，名下平台账号立即绑定，历史成绩才能归到这所学校
            user.sync_platform_accounts_school()

            app.status = AdminApplicationStatus.APPROVED
            app.reviewer = request.user
            app.reviewed_at = timezone.now()
            app.save(update_fields=["status", "reviewer", "reviewed_at"])
            n += 1
        self.message_user(request, f"已通过 {n} 条申请", messages.SUCCESS)

    @admin.action(description="驳回申请")
    def reject(self, request, queryset):
        n = queryset.filter(status=AdminApplicationStatus.PENDING).update(
            status=AdminApplicationStatus.REJECTED,
            reviewer=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"已驳回 {n} 条申请", messages.WARNING)


@admin.register(ScoreConfig)
class ScoreConfigAdmin(admin.ModelAdmin):
    list_display = ("__str__", "cf_factor", "atcoder_factor", "nowcoder_factor",
                    "recent_contest_limit", "rating_decay", "rating_prior")


@admin.register(AtCoderAffiliationAlias)
class AtCoderAffiliationAliasAdmin(admin.ModelAdmin):
    list_display = ("raw_affiliation", "school", "canonical_name", "is_active",
                    "note")
    list_filter = ("is_active",)
    search_fields = ("raw_affiliation", "canonical_name", "school__name")


@admin.register(ScoreRulePage)
class ScoreRulePageAdmin(admin.ModelAdmin):
    """积分规则页（单例）：内容用 Markdown，保存自动升版本号。"""

    list_display = ("version", "updated_at", "updated_by")
    fields = ("content", "version", "updated_by")
    readonly_fields = ("version", "updated_by")

    def has_add_permission(self, request):
        # 单例：已有记录则禁止再增
        return not ScoreRulePage.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if change:
            obj.version = (obj.version or 1) + 1
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
