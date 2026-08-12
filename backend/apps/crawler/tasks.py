"""
Celery 任务：调用 crawlers/ 下已验证的三个爬虫，把结果送进 ingest 层。

爬虫脚本不在 Django 包内（crawlers/ 与 backend/ 平级），
这里通过 sys.path 引入，避免复制一份代码造成两边逻辑漂移。
"""

import logging
import sys
import traceback

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.common.models import Platform
from apps.crawler.ingest import ingest_contest
from apps.crawler.models import CrawlJob

logger = logging.getLogger(__name__)

_CRAWLER_DIR = str(settings.CRAWLER_DIR)
if _CRAWLER_DIR not in sys.path:
    sys.path.insert(0, _CRAWLER_DIR)


def _load_scraper(platform):
    """延迟导入，避免 Django 启动时就依赖爬虫模块。"""
    if platform == Platform.CODEFORCES:
        from cf_scraper import CodeforcesScraper
        return CodeforcesScraper()
    if platform == Platform.ATCODER:
        from atcoder_scraper import AtCoderScraper
        return AtCoderScraper()
    if platform == Platform.NOWCODER:
        from nowcoder_scraper import NowCoderScraper
        return NowCoderScraper()
    raise ValueError(f"未知平台: {platform}")


def _run_job(job, worker):
    """统一的任务生命周期管理：状态流转 + 异常兜底 + 统计回写。"""
    job.status = CrawlJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at", "updated_at"])

    lines = []
    contest_n = part_n = cheat_n = 0
    try:
        for meta, detail in worker():
            result = ingest_contest(job.platform, meta, detail)
            if result.get("skipped"):
                lines.append(f"跳过 {meta.get('name')}: {result.get('reason')}")
                continue
            contest_n += 1
            part_n += result["countable"]
            cheat_n += result["cheaters"]
            lines.append(
                f"{meta.get('name')}: 计分 {result['countable']} 条，"
                f"作弊排除 {result['cheaters']} 条")
        job.status = CrawlJob.Status.SUCCESS
    except Exception as exc:
        job.status = CrawlJob.Status.PARTIAL if contest_n else CrawlJob.Status.FAILED
        job.error_message = f"{exc}\n{traceback.format_exc()}"[:4000]
        logger.exception("爬取任务 #%s 失败", job.pk)
    finally:
        job.finished_at = timezone.now()
        job.contest_count = contest_n
        job.participation_count = part_n
        job.cheater_count = cheat_n
        job.log = "\n".join(lines)[:20000]
        job.save()
    return {"job_id": job.pk, "status": job.status,
            "contests": contest_n, "countable": part_n, "cheaters": cheat_n}


@shared_task(bind=True)
def crawl_codeforces(self, job_id=None, count=20, mode="rating"):
    job = _get_or_create_job(job_id, Platform.CODEFORCES, self.request.id,
                             {"count": count, "mode": mode})

    def worker():
        s = _load_scraper(Platform.CODEFORCES)
        contests = s.parse_contests(s.fetch_contest_list())
        contests = [c for c in contests if not c.get("is_future")][:count]
        contests = s.filter_contests(contests, rated_only=True, exclude_paid=True)
        for c in contests:
            cid = c.get("real_contest_id") or c.get("contest_id")
            yield c, s.scrape_contest_detail(cid, mode=mode)

    return _run_job(job, worker)


@shared_task(bind=True)
def crawl_atcoder(self, job_id=None, count=20):
    job = _get_or_create_job(job_id, Platform.ATCODER, self.request.id,
                             {"count": count})

    def worker():
        s = _load_scraper(Platform.ATCODER)
        contests = s.parse_contests(s.fetch_contest_list())
        contests = s.filter_contests(contests, rated_only=True, exclude_paid=True)
        for c in contests[:count]:
            cid = c.get("contest_id")
            yield c, s.scrape_contest_detail(cid)

    return _run_job(job, worker)


@shared_task(bind=True)
def crawl_nowcoder(self, job_id=None, months=None, months_back=None):
    """牛客最慢（1100 人约 65s），路由到 crawl_slow 队列。

    months: 显式指定 ["YYYY-MM", ...]；
    months_back: 自动取最近 N 个月（与 months 互斥，months 优先）；
    都不传则只抓当前月。
    """
    job = _get_or_create_job(job_id, Platform.NOWCODER, self.request.id,
                             {"months": months, "months_back": months_back})

    def worker():
        s = _load_scraper(Platform.NOWCODER)
        s.init_session()
        if months:
            target = months
        elif months_back:
            target = _last_n_months(months_back)
        else:
            target = [timezone.now().strftime("%Y-%m")]
        contests = []
        for ym in target:
            contests.extend(s.parse_contests(s.fetch_contests(ym)))
        contests = s.filter_contests(contests, rated_only=True, exclude_paid=True)
        for c in contests:
            rid = c.get("real_contest_id")
            if not rid:
                continue
            # exclude_cheaters=False：保留作弊记录进入 ingest，
            # 由入库层打排除标记，保证有据可查
            yield c, s.scrape_contest_detail(rid, filter_post_contest=True,
                                             exclude_cheaters=False)

    return _run_job(job, worker)


def _last_n_months(n):
    """返回最近 n 个月（含当月）的 ['YYYY-MM', ...]，从最早到当月。"""
    now = timezone.now()
    y, m = now.year, now.month
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


def _get_or_create_job(job_id, platform, task_id, params):
    if job_id:
        job = CrawlJob.objects.get(pk=job_id)
        job.celery_task_id = task_id or ""
        job.save(update_fields=["celery_task_id", "updated_at"])
        return job
    return CrawlJob.objects.create(
        platform=platform,
        celery_task_id=task_id or "",
        params=params or {},
    )
