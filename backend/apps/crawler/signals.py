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
    - 间隔 >1 天：每隔 N 天在 **00:00（Asia/Shanghai）** 触发，不看触发小时
      （用户原设计）。Celery 的 IntervalSchedule 无钟点概念，due = last_run_at
      + N 天，因此保存配置时把 last_run_at 基准规整到最近一个已过去的 00:00——
      下次触发 = 基准 + N 天 = 未来的某天 00:00；此后任务恰在 00:00 运行，
      last_run_at 自然保持整点，周期自洽，无需额外维护。
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
        pt.last_run_at = _last_midnight()
    pt.enabled = instance.enabled
    pt.save(update_fields=["crontab", "interval", "enabled", "last_run_at"])


def _last_midnight():
    """最近一个已过去的 00:00（Asia/Shanghai），作为多天间隔的触发基准。"""
    from django.utils import timezone as dj_tz

    now = dj_tz.localtime(dj_tz.now())
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.replace(tzinfo=dj_tz.get_current_timezone())
