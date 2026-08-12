from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import PlatformAccount, User


class PlatformAccountInline(admin.TabularInline):
    model = PlatformAccount
    extra = 0
    fields = ("platform", "handle", "display_name", "school", "verified")
    readonly_fields = ("school",)  # 由用户学校同步而来，不在这里直接改


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "real_name", "role", "school",
                    "is_active", "date_joined")
    list_filter = ("role", "school", "is_active")
    search_fields = ("username", "real_name", "email", "student_no",
                     "passport_user_id")
    inlines = [PlatformAccountInline]
    actions = ["sync_school_to_accounts"]

    fieldsets = BaseUserAdmin.fieldsets + (
        ("业务信息", {"fields": ("role", "school", "real_name", "student_no",
                              "passport_user_id", "school_bound_at")}),
    )

    @admin.action(description="将学校同步到名下平台账号")
    def sync_school_to_accounts(self, request, queryset):
        total = sum(u.sync_platform_accounts_school() for u in queryset)
        self.message_user(request, f"已同步 {total} 个平台账号的学校归属",
                          messages.SUCCESS)


@admin.register(PlatformAccount)
class PlatformAccountAdmin(admin.ModelAdmin):
    list_display = ("handle", "platform", "user", "school", "verified")
    list_filter = ("platform", "verified", "school")
    search_fields = ("handle", "display_name", "user__username")
    raw_id_fields = ("user",)
    readonly_fields = ("handle_lower",)
