from django.contrib import admin, messages
from django.utils.html import format_html

from apps.common.models import ExcludeReason

from .models import Contest, Participation, Problem


class ProblemInline(admin.TabularInline):
    model = Problem
    extra = 0
    fields = ("index", "title", "full_score", "solved_count")


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ("name", "platform", "start_time", "rated_badge",
                    "participant_count", "valid_participant_count",
                    "cheater_badge", "difficulty_factor")
    list_filter = ("platform", "is_rated", "is_paid", "series")
    search_fields = ("name", "external_id")
    date_hierarchy = "start_time"
    readonly_fields = ("rated_source", "rated_comment", "raw_meta", "crawled_at",
                       "participant_count", "valid_participant_count",
                       "cheater_count")
    inlines = [ProblemInline]

    @admin.display(description="计分")
    def rated_badge(self, obj):
        if obj.is_paid:
            return format_html('<span style="color:#c0392b">付费·不计分</span>')
        if not obj.is_rated:
            return format_html('<span style="color:#7f8c8d">unrated</span>')
        return format_html('<span style="color:#27ae60">rated</span>')

    @admin.display(description="作弊")
    def cheater_badge(self, obj):
        if obj.cheater_count:
            return format_html('<b style="color:#c0392b">{}</b>', obj.cheater_count)
        return "-"


@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ("handle", "display_name", "contest", "rank",
                    "platform_account", "exclude_badge")
    list_filter = ("is_excluded", "exclude_reason", "contest__platform")
    search_fields = ("handle", "display_name", "raw_display_name")
    raw_id_fields = ("contest", "platform_account")
    readonly_fields = ("raw_display_name", "score_detail", "extra")
    actions = ["mark_excluded", "unmark_excluded"]

    @admin.display(description="状态")
    def exclude_badge(self, obj):
        if not obj.is_excluded:
            return format_html('<span style="color:#27ae60">计分</span>')
        color = "#c0392b" if obj.exclude_reason == ExcludeReason.CHEATER else "#7f8c8d"
        return format_html('<span style="color:{}">{}</span>',
                           color, obj.get_exclude_reason_display())

    @admin.action(description="人工剔除所选记录")
    def mark_excluded(self, request, queryset):
        n = queryset.update(is_excluded=True, exclude_reason=ExcludeReason.MANUAL)
        self.message_user(request, f"已剔除 {n} 条记录", messages.SUCCESS)

    @admin.action(description="恢复计分（作弊记录不可恢复）")
    def unmark_excluded(self, request, queryset):
        # 作弊是平台判定的客观事实，不允许在后台一键洗白
        blocked = queryset.filter(exclude_reason=ExcludeReason.CHEATER).count()
        n = queryset.exclude(exclude_reason=ExcludeReason.CHEATER).update(
            is_excluded=False, exclude_reason="")
        msg = f"已恢复 {n} 条记录"
        if blocked:
            msg += f"；{blocked} 条作弊记录被拒绝恢复"
        self.message_user(request, msg,
                          messages.WARNING if blocked else messages.SUCCESS)
