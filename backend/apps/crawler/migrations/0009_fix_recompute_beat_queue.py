"""把 recompute-ranking-daily 的队列从 default 改成 crawl。

`0002_beat_schedules` 当年把这条调度写成 `queue="default"`，而生产 worker 只消费
`crawl,crawl_slow`（docker-compose.yml 的启动命令）。PeriodicTask 显式带队列会**盖过**
`CELERY_TASK_ROUTES`，所以 2026-08-13 补上的路由（apps.ranking.tasks.* → crawl）
对 beat 派发完全无效：每日 04:00 的重算消息一直堆在 default 里没人取。
2026-10-18 实测 `LLEN default = 60`，其中 51 条是 recompute_ranking_task，
最早一条可追溯到 2026-08-29 —— 榜单只靠爬取结束后内联派发维持。

用 save() 而不是 queryset.update()：django_celery_beat 靠 post_save 记账
`PeriodicTasks.last_update`，DatabaseScheduler 据此判断要不要重载调度表；
`update()` 绕过信号，改完 beat 进程里还是旧的 default 条目。

迁移幂等：已经是 crawl 的行再跑一次不产生第二次写。
"""
import json

from django.db import migrations
from django_celery_beat.models import CrontabSchedule, PeriodicTask

SCHEDULE_TZ = "Asia/Shanghai"
TASK_NAME = "recompute-ranking-daily"
TASK_PATH = "apps.ranking.tasks.recompute_ranking_task"
BROKEN_QUEUE = "default"
FIXED_QUEUE = "crawl"


def _cron():
    cron, _ = CrontabSchedule.objects.get_or_create(
        minute="0", hour="4", day_of_week="*", day_of_month="*",
        month_of_year="*", timezone=SCHEDULE_TZ,
    )
    return cron


def forward(apps, schema_editor):
    pt = PeriodicTask.objects.filter(name=TASK_NAME).first()
    if pt is None:
        # 行被人为删过：按 0002 的规格补建，队列直接用修好的值，
        # 免得「补建」变成第二次把黑洞写回去的机会。
        pt = PeriodicTask(
            name=TASK_NAME,
            task=TASK_PATH,
            crontab=_cron(),
            kwargs=json.dumps({"scope": "all"}),
            queue=FIXED_QUEUE,
            enabled=True,
        )
    if pt.queue != FIXED_QUEUE:
        pt.queue = FIXED_QUEUE
        pt.save()


def reverse(apps, schema_editor):
    pt = PeriodicTask.objects.filter(name=TASK_NAME).first()
    if pt is not None and pt.queue == FIXED_QUEUE:
        pt.queue = BROKEN_QUEUE
        pt.save()


class Migration(migrations.Migration):
    dependencies = [
        ("crawler", "0008_alter_crawljob_platform"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
