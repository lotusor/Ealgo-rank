from django.apps import AppConfig


class CrawlerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.crawler"
    verbose_name = "爬虫任务"

    def ready(self):
        from . import signals  # noqa: F401 注册 CrawlConfig -> Beat 同步信号
        # 排期源与注册表的覆盖必须一致，否则某个平台会在日历里静默缺席
        from apps.crawler.tasks import check_calendar_wiring

        check_calendar_wiring()
