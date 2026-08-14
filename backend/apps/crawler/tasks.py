"""
Celery 任务：调用 crawlers/ 下已验证的三个爬虫，把结果送进 ingest 层。

爬虫脚本不在 Django 包内（crawlers/ 与 backend/ 平级），
这里通过 sys.path 引入，避免复制一份代码造成两边逻辑漂移。
"""

import json
import logging
import socket
import sys
import threading
import traceback
from urllib.parse import urlparse

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.common.models import Platform
from apps.crawler.ingest import ingest_contest
from apps.crawler.models import CrawlConfig, CrawlJob

logger = logging.getLogger(__name__)

_CRAWLER_DIR = str(settings.CRAWLER_DIR)
if _CRAWLER_DIR not in sys.path:
    sys.path.insert(0, _CRAWLER_DIR)

# 去重窗口：同一平台 + 相同参数在此时长内已有进行中任务，则不再重复派发
DEDUP_WINDOW = timezone.timedelta(hours=1)


def _broker_reachable():
    """快速探测 broker（Redis）是否可达。

    本沙箱里连到未监听的本地端口会“黑洞”而非立即 refused，导致 Celery
    的 .delay() 阻塞数十秒；这里用 2s 超时原生 socket 探测，快速判定。
    """
    raw = getattr(settings, "CELERY_BROKER_URL", "") or "redis://127.0.0.1:6379/0"
    parsed = urlparse(raw)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def _dispatch_crawl(task, job_id, params):
    """后台派发 Celery 任务。

    broker 不可达（Redis 未启动等）时：先快速探测，不可达则直接标记 failed，
    避免阻塞；可达则 dispatch（生产环境 Redis 在线时为瞬时操作）。
    """
    if not _broker_reachable():
        CrawlJob.objects.filter(pk=job_id).update(
            status=CrawlJob.Status.FAILED,
            error_message="任务派发失败：无法连接消息队列，请确认 Redis / Celery worker 已启动",
        )
        return
    try:
        task.delay(job_id=job_id, **params)
    except Exception as exc:  # noqa: BLE001 - 任何派发异常都标记失败
        CrawlJob.objects.filter(pk=job_id).update(
            status=CrawlJob.Status.FAILED,
            error_message=f"任务派发失败：{exc}",
        )


def _normalize_params(params):
    """把任务参数规范化为可比较的字符串（用于去重）。"""
    return json.dumps(params or {}, sort_keys=True, default=str)


def active_duplicate_exists(platform, params):
    """同一平台 + 相同参数在去重窗口内是否已有进行中（pending/running）任务。

    不去依赖 JSON 列的精确匹配（存储格式化可能不一致），而是在 Python 内
    对归一化参数做比较，更稳健。
    """
    cutoff = timezone.now() - DEDUP_WINDOW
    target = _normalize_params(params)
    for job in CrawlJob.objects.filter(
        platform=platform,
        status__in=[CrawlJob.Status.PENDING, CrawlJob.Status.RUNNING],
        created_at__gte=cutoff,
    ):
        if _normalize_params(job.params) == target:
            return job
    return None


def create_crawl_job(platform, params, triggered_by=None):
    """创建爬取任务，带重复防护。

    返回 (job, created)。若去重窗口内已有进行中同参数任务，返回 (原 job, False)，
    不新建，避免重复爬取。
    """
    existing = active_duplicate_exists(platform, params)
    if existing is not None:
        return existing, False
    job = CrawlJob.objects.create(
        platform=platform, triggered_by=triggered_by, params=params or {})
    return job, True


def enqueue_crawl(platform, params, triggered_by=None):
    """统一的爬取派发入口（手动触发与定时任务共用）。

    先创建 CrawlJob（带去重），再后台派发 Celery 任务；返回创建的 job
    （去重命中时返回既有的进行中 job）。
    """
    job, _created = create_crawl_job(platform, params, triggered_by=triggered_by)
    if job is None:
        return None
    task = TASK_MAP[platform]
    # 后台派发，避免 broker 不可达时阻塞调用线程
    threading.Thread(
        target=_dispatch_crawl, args=(task, job.pk, params),
        daemon=True, name=f"dispatch-crawl-{job.pk}",
    ).start()
    return job


@shared_task
def auto_crawl_task():
    """定时自动激活爬虫（由 Celery Beat 每日调用）。

    读取 CrawlConfig：未启用则跳过；否则按配置窗口为三大平台各派发一次爬取。
    派发本身走 enqueue_crawl，自带重复防护（不会因 beat 抖动重复爬取）。
    """
    cfg = CrawlConfig.get_config()
    if not cfg.enabled:
        logger.info("自动爬取已停用（CrawlConfig.enabled=False），跳过本次调度")
        return {"skipped": True, "reason": "disabled"}

    plans = [
        (Platform.CODEFORCES, {"count": cfg.cf_count, "mode": "rating"}),
        (Platform.ATCODER, {"count": cfg.atcoder_count}),
        (Platform.NOWCODER, {"months_back": cfg.nowcoder_months_back}),
    ]
    created = []
    for platform, params in plans:
        job = enqueue_crawl(platform, params, triggered_by=None)
        if job is not None:
            created.append(job.pk)

    logger.info("自动爬取已派发 %d 个平台任务: %s", len(created), created)
    return {"dispatched": created}


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


# 平台 -> 对应 Celery 爬取任务（定义于本文件上方，放在末尾避免循环引用时的未定义问题）
TASK_MAP = {
    Platform.CODEFORCES: crawl_codeforces,
    Platform.ATCODER: crawl_atcoder,
    Platform.NOWCODER: crawl_nowcoder,
}
