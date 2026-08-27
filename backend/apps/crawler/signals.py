"""CrawlConfig 变更时同步 Celery Beat 调度。"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_celery_beat.models import (CrontabSchedule, IntervalSchedule,
                                       PeriodicTask)

from apps.crawler.models import CrawlConfig

AUTO_CRAWL_TASK_NAME = "auto-crawl-daily"
SCHEDULE_TZ = "Asia/Shanghai"


@receiver(post_save, sender=CrawlConfig)
def sync_auto_crawl_schedule(sender, instance, **kwargs):
    """CrawlConfig 保存后：把自动爬取的间隔与启用状态同步到 beat 调度条目。

    - 间隔 1 天：crontab 每天固定小时触发（精确到 auto_crawl_hour 点）。
    - 间隔 >1 天：IntervalSchedule(DAYS, every=N)，触发钟点无法用 interval
      表达，以 beat 首次派发时刻为基准，后续每 N 天一次。
    """
    try:
        pt = PeriodicTask.objects.get(name=AUTO_CRAWL_TASK_NAME)
    except PeriodicTask.DoesNotExist:
        return

    interval = max(1, int(instance.auto_crawl_interval_days or 1))
    if interval == 1:
        cron, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour=str(instance.auto_crawl_hour),
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
            timezone=SCHEDULE_TZ,
        )
        pt.crontab = cron
        pt.interval = None
    else:
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=interval,
            period=IntervalSchedule.DAYS,
        )
        pt.interval = schedule
        pt.crontab = None
    pt.enabled = instance.enabled
    pt.save(update_fields=["crontab", "interval", "enabled"])
