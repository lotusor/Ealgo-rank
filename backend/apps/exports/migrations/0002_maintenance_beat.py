"""注册导出维护调度（每小时清理卡死任务 + 过期文件 + 磁盘配额）。

为什么要这条 beat：`purge_expired_exports` 不跑，过期文件会一直躺在
`./volumes/exports` 里，而「下载有效期 2 小时」就只剩数据库里的一个字段、
文件其实还能通过内部路径读到。清理与过期必须成对存在。

`queue="export"` 必须显式写：PeriodicTask 上带的队列会**盖过**
`CELERY_TASK_ROUTES`。生产 worker 启动命令已含 export（docker-compose.yml）。
写错的后果与 0009 修的那个坑同源——消息堆在没人消费的队列里。
"""
import json

from django.db import migrations
from django_celery_beat.models import CrontabSchedule, PeriodicTask

SCHEDULE_TZ = "Asia/Shanghai"
TASK_NAME = "export-maintenance"
TASK_PATH = "apps.exports.tasks.export_maintenance_task"
QUEUE = "export"


def _cron():
    cron, _ = CrontabSchedule.objects.get_or_create(
        minute="5", hour="*", day_of_week="*", day_of_month="*",
        month_of_year="*", timezone=SCHEDULE_TZ,
    )
    return cron


def forward(apps, schema_editor):
    pt = PeriodicTask.objects.filter(name=TASK_NAME).first()
    if pt is None:
        PeriodicTask.objects.create(
            name=TASK_NAME,
            task=TASK_PATH,
            crontab=_cron(),
            queue=QUEUE,
            enabled=True,
        )
        return
    changed = False
    if pt.queue != QUEUE:
        pt.queue = QUEUE
        changed = True
    if not pt.enabled:
        pt.enabled = True
        changed = True
    if changed:
        pt.save()


def reverse(apps, schema_editor):
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("exports", "0001_initial"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
