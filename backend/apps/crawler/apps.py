from django.apps import AppConfig


class CrawlerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.crawler"
    verbose_name = "爬虫任务"

    def ready(self):
        from . import signals  # noqa: F401 注册 CrawlConfig -> Beat 同步信号
