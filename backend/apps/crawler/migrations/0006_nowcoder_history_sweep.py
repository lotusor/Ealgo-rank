"""新增每日牛客历史巡检调度 nowcoder-history-sweep。

绑定时的定向补数只解决「即时」，派发失败（broker 抖动、worker 回收、平台
接口被拦）会让某个用户的历史永久缺着；本调度每天兜一次，保证最终一致。
05:00 Asia/Shanghai：错开 00:00 的自动爬取与 04:00 的积分重算。
迁移幂等：重复执行不会重复建条目。
"""
import json

from django.db import migrations
from django_celery_beat.models import CrontabSchedule, PeriodicTask

SCHEDULE_TZ = "Asia/Shanghai"
TASK_NAME = "nowcoder-history-sweep"


def forward(apps, schema_editor):
    cron, _ = CrontabSchedule.objects.get_or_create(
        minute="0", hour="5", day_of_week="*", day_of_month="*",
        month_of_year="*", timezone=SCHEDULE_TZ,
    )
    PeriodicTask.objects.update_or_create(
        name=TASK_NAME,
        defaults={
            "task": "apps.crawler.tasks.sweep_nowcoder_history",
            "crontab": cron,
            "kwargs": json.dumps({"max_accounts": 5}),
            "queue": "crawl",
            "enabled": True,
        },
    )


def reverse(apps, schema_editor):
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("crawler", "0005_crawlconfig_auto_crawl_interval_days_and_more"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
