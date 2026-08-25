"""清理卡在 running / pending 状态的僵尸爬取任务。

场景：Celery worker 重启、任务派发失败、或进程被杀时，CrawlJob 可能停留在
running / pending 而永远不流转到终态。这些僵尸记录虽不阻塞后续去重（去重
窗口仅 1 小时），但会污染后台「爬取记录」列表展示。

用法：
    python manage.py stale_crawl_jobs            # 只列出僵尸任务（dry-run）
    python manage.py stale_crawl_jobs --hours 6  # 超过 6 小时仍未结束视为僵尸
    python manage.py stale_crawl_jobs --fix      # 实际标记为 failed

默认超时阈值：牛客任务软超时 55 分钟、硬超时 60 分钟，故取 2 小时为安全阈值，
远大于任一平台任务最长生命周期，不会误杀仍在跑的合法任务。
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.crawler.models import CrawlJob

logger = logging.getLogger(__name__)

DEFAULT_HOURS = 2


class Command(BaseCommand):
    help = "清理卡在 running/pending 超过 N 小时的僵尸爬取任务"

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=DEFAULT_HOURS,
                            help=f"超过该小时数仍未结束即视为僵尸（默认 {DEFAULT_HOURS}）")
        parser.add_argument("--fix", action="store_true",
                            help="实际标记为 failed；缺省只列出（dry-run）")

    def handle(self, *args, **options):
        hours = options["hours"]
        do_fix = options["fix"]
        cutoff = timezone.now() - timezone.timedelta(hours=hours)

        qs = CrawlJob.objects.filter(
            status__in=[CrawlJob.Status.PENDING, CrawlJob.Status.RUNNING],
            created_at__lt=cutoff,
        )

        n = qs.count()
        if n == 0:
            self.stdout.write("没有卡住的僵尸爬取任务。")
            return

        for job in qs:
            self.stdout.write(
                f"  #%d %s %s（created=%s）" % (
                    job.pk, job.platform, job.status,
                    timezone.localtime(job.created_at).strftime("%Y-%m-%d %H:%M:%S")))

        if do_fix:
            updated = qs.update(
                status=CrawlJob.Status.FAILED,
                error_message=f"任务卡在 {job.status} 超过 {hours} 小时，"
                              f"由 stale_crawl_jobs 自动标记为失败",
                finished_at=timezone.now(),
            )
            self.stdout.write(self.style.SUCCESS(f"已标记 {updated} 条为 failed。"))
        else:
            self.stdout.write(
                self.style.WARNING(f"共 {n} 条僵尸任务（dry-run，未修改）。"
                                   "加 --fix 实际标记。"))
