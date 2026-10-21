"""将 Beat 中三个按平台爬取任务，替换为统一的 auto-crawl 调度。

原调度（0002）把爬取窗口硬编码在迁移里，且无法由运营在后台启停/调参。
现改为单一 `auto-crawl-daily` 任务，运行时读取 CrawlConfig（启用开关、各平台
抓取场数/月数、触发小时），实现「设置定时任务自动激活爬虫」。CrawlConfig 变更
时由 signals 同步 beat 的 crontab 小时与 enabled。

保留 recompute-ranking-daily（独立重算任务）。
迁移幂等：重复执行不会重复建/删条目。
"""
from django.db import migrations
import json

from django_celery_beat.models import CrontabSchedule, PeriodicTask

SCHEDULE_TZ = "Asia/Shanghai"

OLD_TASK_NAMES = [
    "crawl-codeforces-daily",
    "crawl-atcoder-daily",
    "crawl-nowcoder-weekly",
]

NEW_TASK = {
    "name": "auto-crawl-daily",
    "task": "apps.crawler.tasks.auto_crawl_task",
    "queue": "crawl",
    "cron": {"minute": "0", "hour": "2", "day_of_week": "*"},
    "kwargs": {},
    "enabled": True,
}


def _ensure_cron(spec):
    sched, _ = CrontabSchedule.objects.get_or_create(
        minute=spec["minute"],
        hour=spec["hour"],
        day_of_week=spec["day_of_week"],
        day_of_month="*",
        month_of_year="*",
        timezone=SCHEDULE_TZ,
    )
    return sched


def forward(apps, schema_editor):
    PeriodicTask.objects.filter(name__in=OLD_TASK_NAMES).delete()
    cron = _ensure_cron(NEW_TASK["cron"])
    PeriodicTask.objects.update_or_create(
        name=NEW_TASK["name"],
        defaults={
            "task": NEW_TASK["task"],
            "crontab": cron,
            "kwargs": json.dumps(NEW_TASK["kwargs"]),
            "queue": NEW_TASK["queue"],
            "enabled": NEW_TASK["enabled"],
        },
    )


def reverse(apps, schema_editor):
    PeriodicTask.objects.filter(name=NEW_TASK["name"]).delete()
    # 回滚为 0002 的默认三平台调度（与 0002 保持一致）
    specs = [
        ("crawl-codeforces-daily", "apps.crawler.tasks.crawl_codeforces",
         "crawl", {"minute": "0", "hour": "2", "day_of_week": "*"}, {"count": 20, "mode": "rating"}),
        ("crawl-atcoder-daily", "apps.crawler.tasks.crawl_atcoder",
         "crawl", {"minute": "30", "hour": "2", "day_of_week": "*"}, {"count": 20}),
        ("crawl-nowcoder-weekly", "apps.crawler.tasks.crawl_nowcoder",
         "crawl_slow", {"minute": "0", "hour": "3", "day_of_week": "0"}, {"months_back": 2}),
    ]
    for name, task, queue, cron, kwargs in specs:
        c = _ensure_cron(cron)
        PeriodicTask.objects.update_or_create(
            name=name,
            defaults={"task": task, "crontab": c, "kwargs": json.dumps(kwargs),
                      "queue": queue, "enabled": True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("crawler", "0003_crawlconfig"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
