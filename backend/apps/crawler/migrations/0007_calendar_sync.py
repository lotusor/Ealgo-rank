"""新增每日日历排期同步 calendar-sync。

站内比赛只在「已结束」爬取窗口内产生，未开赛的官方排期从不落库，
`status=upcoming` 实测恒为 0（HANDOVER §0.26）——日历页因此永远空。本调度每天
用 clist.by 的聚合排期刷新日历行（未开赛 + 进行中），日历才有「即将开始」。

03:00 Asia/Shanghai：避开 00:00 自动爬取、04:00 积分重算、05:00 牛客历史巡检。
queue 必须显式 crawl —— 生产 worker 只消费 crawl,crawl_slow，落到 default 会被
静默黑洞（recompute-ranking-daily 即此形态，见 §0.13）。
迁移幂等：重复执行不重复建条目。
"""
import json

from django.db import migrations
from django_celery_beat.models import CrontabSchedule, PeriodicTask

SCHEDULE_TZ = "Asia/Shanghai"
TASK_NAME = "calendar-sync"


def forward(apps, schema_editor):
    cron, _ = CrontabSchedule.objects.get_or_create(
        minute="0", hour="3", day_of_week="*", day_of_month="*",
        month_of_year="*", timezone=SCHEDULE_TZ,
    )
    PeriodicTask.objects.update_or_create(
        name=TASK_NAME,
        defaults={
            "task": "apps.crawler.tasks.sync_calendar_contests",
            "crontab": cron,
            # 不写死参数：前瞻窗口由 settings.CALENDAR_AHEAD_DAYS 单点决定，
            # 在这里钉一份数字会变成两个真相
            "kwargs": json.dumps({}),
            "queue": "crawl",
            "enabled": True,
        },
    )


def reverse(apps, schema_editor):
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("crawler", "0006_nowcoder_history_sweep"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
