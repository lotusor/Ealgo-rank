from django.apps import AppConfig


class ContestsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.contests"
    verbose_name = "比赛与成绩"

    def ready(self):
        # 平台枚举 ↔ 注册表 ↔ 模型字段的对齐检查。本仓库没有 CI，这类「加了平台
        # 忘了配下一处」的错只会在线上表现为数据不对，所以在启动期就拦住。
        from apps.common.platforms import validate_registry

        validate_registry()
