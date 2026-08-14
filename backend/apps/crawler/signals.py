"""CrawlConfig 变更时同步 Celery Beat 调度。"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from apps.crawler.models import CrawlConfig

AUTO_CRAWL_TASK_NAME = "auto-crawl-daily"
SCHEDULE_TZ = "Asia/Shanghai"


@receiver(post_save, sender=CrawlConfig)
def sync_auto_crawl_schedule(sender, instance, **kwargs):
    """CrawlConfig 保存后：把自动爬取的小时与启用状态同步到 beat 调度条目。"""
    try:
        pt = PeriodicTask.objects.get(name=AUTO_CRAWL_TASK_NAME)
    except PeriodicTask.DoesNotExist:
        return
    cron, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour=str(instance.auto_crawl_hour),
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone=SCHEDULE_TZ,
    )
    pt.crontab = cron
    pt.enabled = instance.enabled
    pt.save(update_fields=["crontab", "enabled"])
