"""建立 Celery beat 定时调度（django-celery-beat 的 DB 调度条目）。

调度规则（与 #6 决策一致）：
- Codeforces：每日 02:00 爬最近 20 场（rating 模式）
- AtCoder：    每日 02:30 爬最近 20 场
- NowCoder：   每周日 03:00 爬最近 2 个月（crawl_slow 队列，最慢）
- 积分重算：   每日 04:00 全量重算（在爬取全部结束后，独立 beat）

使用 DatabaseScheduler，故调度条目必须落在 DB；本迁移在 migrate 时
幂等写入，重复执行不会重复建条目。
"""
from django.db import migrations
import json

from django_celery_beat.models import CrontabSchedule, PeriodicTask

SCHEDULE_TZ = "Asia/Shanghai"

SCHEDULES = [
    {
        "name": "crawl-codeforces-daily",
        "task": "apps.crawler.tasks.crawl_codeforces",
        "queue": "crawl",
        "cron": {"minute": "0", "hour": "2", "day_of_week": "*"},
        "kwargs": {"count": 20, "mode": "rating"},
    },
    {
        "name": "crawl-atcoder-daily",
        "task": "apps.crawler.tasks.crawl_atcoder",
        "queue": "crawl",
        "cron": {"minute": "30", "hour": "2", "day_of_week": "*"},
        "kwargs": {"count": 20},
    },
    {
        "name": "crawl-nowcoder-weekly",
        "task": "apps.crawler.tasks.crawl_nowcoder",
        "queue": "crawl_slow",
        "cron": {"minute": "0", "hour": "3", "day_of_week": "0"},  # 0=周日
        "kwargs": {"months_back": 2},
    },
    {
        "name": "recompute-ranking-daily",
        "task": "apps.ranking.tasks.recompute_ranking_task",
        "queue": "default",
        "cron": {"minute": "0", "hour": "4", "day_of_week": "*"},
        "kwargs": {"scope": "all"},
    },
]


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


def create_schedules(apps, schema_editor):
    for s in SCHEDULES:
        cron = _ensure_cron(s["cron"])
        PeriodicTask.objects.update_or_create(
            name=s["name"],
            defaults={
                "task": s["task"],
                "crontab": cron,
                "kwargs": json.dumps(s["kwargs"]),
                "queue": s["queue"],
                "enabled": True,
            },
        )


def remove_schedules(apps, schema_editor):
    PeriodicTask.objects.filter(
        name__in=[s["name"] for s in SCHEDULES]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("crawler", "0001_initial"),
        # 必须在 django_celery_beat 的 timezone 列（CrontabSchedule）建立之后，
        # 否则全新测试库 migrate 时本迁移的 get_or_create(timezone=...) 会因
        # 列不存在而失败（开发库因 beat 早已全量迁移而幸免）。
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_schedules, remove_schedules),
    ]
