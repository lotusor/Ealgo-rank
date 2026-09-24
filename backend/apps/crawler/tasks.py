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
from datetime import datetime
from urllib.parse import urlparse

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from pathlib import Path

from apps.accounts.models import PlatformAccount
from apps.common.models import Platform
from apps.contests.models import Contest, Participation
from apps.crawler.ingest import (CALENDAR_RATED_SOURCE, ingest_contest)
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


def relevant_contest_ids(platform):
    """返回该平台下「有已关联平台ID用户参与」的比赛 external_id 集合。

    即所有 PlatformAccount.participated_contests 的并集。爬虫预筛用它跳过
    无人参与的比赛，避免下载无关全量榜单（带宽大头）。
    """
    ids = set()
    for acc in PlatformAccount.objects.filter(platform=platform):
        for cid in (acc.participated_contests or []):
            ids.add(str(cid))
    return ids


def _crawler_cache_dir(platform):
    """持久缓存目录（按平台分子目录）；未配置则关闭缓存。"""
    base = getattr(settings, "CRAWLER_CACHE_DIR", None)
    if not base:
        return None
    return str(Path(base) / platform)


def _contest_end_dt(contest_meta):
    """比赛结束时间（aware）；解析失败返回 None。"""
    raw = (contest_meta or {}).get("end_time") or (contest_meta or {}).get("start_time")
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _contest_cache_ttl(contest_meta):
    """落盘缓存有效期：已结束满 N 天的比赛榜单已冻结，缓存不再失效。

    否则每轮爬取都要把整场榜单重新分页下载（牛客每页 50 条 + 1.5~3.5s 延时，
    实测单场 90~300 秒）， crawl_nowcoder 的 55 分钟软超时只够处理最新几十场，
    「已入库但缺新绑定用户行」的历史场次永远排不到 —— 2026-09-22 学生榜
    第一名 21 场历史缺失即此因（榜单原文其实已在本地缓存里）。
    """
    ttl = getattr(settings, "CRAWLER_CACHE_TTL_HOURS", 168)
    days = getattr(settings, "CRAWLER_IMMUTABLE_AFTER_DAYS", 7)
    if not days:
        return ttl
    end = _contest_end_dt(contest_meta)
    if end is None:
        return ttl
    return None if timezone.now() - end > timezone.timedelta(days=days) else ttl


def _relevant_handles(platform):
    """本平台全部已关联平台ID用户的 handle（用于只为这些人补齐每题明细）。"""
    return list(PlatformAccount.objects.filter(platform=platform)
                .values_list("handle", flat=True))


def _prune_ingested_history(platform, history_contests):
    """剪掉「已入库且无新绑定用户待补行」的历史比赛。

    重放一场已入库比赛的唯一价值：给新绑定的用户补参与行（ingest 幂等
    update_or_create）。若该场所有索引指向的账号在库里都已有行，重放无
    信息增益，直接剪掉——避免用户量增长后索引历史每轮全量重放缓存。

    返回仍需抓取详情的子集；未入库的场次一律保留（含新绑定用户带出的
    历史月，2026-09 曾因 50 场截断线被永久挡住，修复后不受上限约束）。
    """
    if not history_contests:
        return []
    ext_ids = []
    for c in history_contests:
        rid = str(c.get("real_contest_id") or c.get("contest_id") or "")
        if rid:
            ext_ids.append(rid)
    ingested = {
        c.external_id: c.id
        for c in Contest.objects.filter(platform=platform, external_id__in=ext_ids)
        # 排期行不是「已入库」：把它算进来会让这场被永久剪出抓取列表，
        # 赛后真榜单就再也没有入口（与 ingest.backfill_account_history 同一防线）
        .exclude(rated_source=CALENDAR_RATED_SOURCE)
    }
    # external_id -> 需要该场成绩的账号 id 集合（来自参与索引）
    need = {}
    for acc in PlatformAccount.objects.filter(platform=platform):
        for cid in (acc.participated_contests or []):
            need.setdefault(str(cid), set()).add(acc.id)
    # 库里已存在的 (contest_id, account_id) 参与行
    existing = set(
        Participation.objects
        .filter(contest_id__in=list(ingested.values()))
        .exclude(platform_account=None)
        .values_list("contest_id", "platform_account_id")
    )
    out = []
    for c in history_contests:
        rid = str(c.get("real_contest_id") or c.get("contest_id") or "")
        contest_id = ingested.get(rid)
        if contest_id is None:
            out.append(c)          # 未入库 → 必须抓
            continue
        pending = need.get(rid, set())
        if any((contest_id, aid) not in existing for aid in pending):
            out.append(c)          # 有账号缺行 → 重放补行
    return out


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

    # 有实际入库（比赛数>0）时触发积分重算，让新抓的成绩立即进入榜单，
    # 而非等到每日 04:00 的 beat 重算。
    # 注意：这里必须「同步」派发，不能用 daemon 线程——Celery prefork worker 里
    # 任务返回后进程被复用/关闭，daemon 线程可能在 .delay() 真正发出前就被杀，
    # 导致 recompute 消息静默丢失（曾出现 40 条 countable 只有 39 条 ScoreRecord）。
    # broker 在线时 .delay() 是瞬时操作（几十 ms），阻塞可忽略。
    if contest_n:
        if not _broker_reachable():
            logger.warning("爬取完成但 broker 不可达，跳过自动重算（待每日 04:00 beat 兜底）")
        else:
            try:
                from apps.ranking.tasks import recompute_ranking_task
                recompute_ranking_task.delay()
                logger.info("爬取完成，已派发积分重算任务")
            except Exception as exc:  # noqa: BLE001
                logger.warning("爬取后积分重算派发失败: %s", exc)

    # 牛客榜单不含 rating，必须事后走 rating-history 回填涨落。
    # 回填挂在「独立任务」而不是爬取生成器的尾部：爬取被 SoftTimeLimitExceeded
    # 打断时生成器直接作废，尾部代码一行都不会执行（2026-09-21/22 两次实测），
    # 于是所有新入库的牛客记录都没有涨落、折线图空、平台 rating 卡片消失。
    # 无论爬取 success / partial / failed，只要跑过就派发，新任务有独立时间预算。
    if job.platform == Platform.NOWCODER and _broker_reachable():
        try:
            backfill_nowcoder_ratings_task.delay()
            logger.info("已派发牛客 rating 涨落回填任务")
        except Exception as exc:  # noqa: BLE001
            logger.warning("牛客 rating 回填派发失败: %s", exc)

    return {"job_id": job.pk, "status": job.status,
            "contests": contest_n, "countable": part_n, "cheaters": cheat_n}


@shared_task
def backfill_nowcoder_ratings_task(account_ids=None):
    """牛客 rating 涨落回填（独立任务）。

    必须独立于爬取任务：爬取被软超时打断时，写在爬取生成器尾部的回填一行
    都不会执行，实测 2026-09-21/22 两轮连续如此，导致新入库的牛客成绩全部
    没有涨落、个人页平台 rating 卡片整块消失。
    """
    from apps.crawler.ingest import backfill_nowcoder_ratings
    return backfill_nowcoder_ratings(account_ids=account_ids)


@shared_task(bind=True, soft_time_limit=60 * 50, time_limit=60 * 55)
def backfill_account_history_task(self, platform_account_id):
    """新绑定账号的定向补数：官方历史索引 → 缺失场次入库 → rating 涨落回填。

    承载方必须是 Celery 而不是 gunicorn 进程内的 daemon 线程：线程会随 worker
    回收被静默杀掉，索引为空的用户在爬取预筛里就永远隐形了。
    """
    from apps.crawler.ingest import (backfill_account_history,
                                     fill_participated_contests)

    try:
        acc = PlatformAccount.objects.get(pk=platform_account_id)
    except PlatformAccount.DoesNotExist:
        logger.info("定向补数：账号 %s 已不存在，跳过", platform_account_id)
        return {"skipped": "gone"}

    # 只有牛客需要「按账号定向补场次」：CF/AtCoder 榜单自带 rating，且历史场次
    # 由预筛索引带出后在本轮爬取里就能抓到。
    if acc.platform != Platform.NOWCODER:
        try:
            filled, n = fill_participated_contests(acc)
            logger.info("官方历史索引刷新：账号 %s 返回 %d 场，更新=%s",
                        acc.handle, n, filled)
        except Exception as exc:  # noqa: BLE001 - 索引补全失败仍可等每日爬取
            logger.warning("索引补全失败 account=%s: %s", acc.handle, exc)
        return {"platform": acc.platform, "index_filled": True}

    # 牛客：backfill_account_history 内部会先 refresh_nowcoder_history（换源索引
    # + 逐行对账），这里再调一次 fill/refresh 就是同一组接口打两遍，故不重复调用。
    result = backfill_account_history(acc)
    v = result.get("verify") or {}
    logger.info("定向补数：账号 %s 待补 %s / 入库 %s，主页对账差异 %s",
                acc.handle, result.get("pending"), result.get("ingested"),
                {k: len(v[k]) for k in
                 ("missing_rows", "rank_diff", "delta_diff", "ac_diff") if v.get(k)})
    if result.get("ingested"):
        if _broker_reachable():
            try:
                from apps.ranking.tasks import recompute_ranking_task
                recompute_ranking_task.delay()
            except Exception as exc:  # noqa: BLE001
                logger.warning("补数后重算派发失败: %s", exc)
        else:
            logger.warning("补数完成但 broker 不可达，积分待每日重算兜底")
    result["index_filled"] = True
    return result


def reap_stale_crawl_jobs(after_hours=3):
    """把卡在 running/pending 超过 after_hours 的爬取任务判为失败。

    worker 被回收或重启会把在跑的任务一起带走，`_run_job` 的 finally 没机会执行
    → 状态永久停在 running（生产实测 job #109 卡了 15 天），管理端因此误报
    「进行中」，去重逻辑也可能被误导。任何爬取的最长预算是 55 分钟，3 小时是安全边界。
    """
    cutoff = timezone.now() - timezone.timedelta(hours=after_hours)
    stale = CrawlJob.objects.filter(
        status__in=[CrawlJob.Status.PENDING, CrawlJob.Status.RUNNING],
        updated_at__lt=cutoff)
    reaped = []
    for job in stale:
        job.status = CrawlJob.Status.FAILED
        job.error_message = ((job.error_message or "") +
                             f"\n状态收割：超过 {after_hours} 小时未结束，"
                             "判定 worker 被回收/重启导致任务中断").strip()
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_message", "finished_at",
                                "updated_at"])
        reaped.append(job.pk)
    if reaped:
        logger.warning("收割卡死的爬取任务: %s", reaped)
    return reaped


@shared_task(bind=True, soft_time_limit=60 * 50, time_limit=60 * 55)
def sweep_nowcoder_history(self, max_accounts=5):
    """每日兜底巡检：补齐「官方索引里有、站内却没有行」的牛客历史场次。

    定向补数解决「即时」，本任务解决「最终一致」：任何一次派发失败都不该让
    某个用户的历史永远缺着。

    每轮对**所有**牛客账号做一次索引刷新 + 官方主页逐行对账（B）：索引换源后
    缺口口径才是全集，对账不挑账号才有信号。`max_accounts` 限制的是**昂贵的
    补数**（要重放榜单）账号数，不限制这条便宜的巡检线。
    """
    from apps.crawler.ingest import (backfill_account_history,
                                     missing_nowcoder_contest_ids,
                                     refresh_nowcoder_history)

    reap_stale_crawl_jobs()
    # 一个 scraper 实例跑完整轮：主页接口有进程级缓存，账号也不会被重复握手
    scraper = _load_scraper(Platform.NOWCODER)
    scraper.init_session()

    touched = []
    still_pending = []
    drift = []
    checked = 0
    budget = max_accounts
    for acc in PlatformAccount.objects.filter(
            platform=Platform.NOWCODER).order_by("id"):
        try:
            res = refresh_nowcoder_history(acc, scraper=scraper)
            acc.refresh_from_db(fields=["participated_contests"])
            m = res["mismatch"]
            if res["rows"]:
                checked += 1
            hits = {k: len(m[k]) for k in
                    ("missing_rows", "rank_diff", "delta_diff", "ac_diff") if m[k]}
            if hits:
                drift.append({"account": acc.pk, **hits,
                              "unrated_rows": len(m["unrated_rows"])})
            if not missing_nowcoder_contest_ids(acc):
                continue
            if budget <= 0:
                break
            budget -= 1
            r = backfill_account_history(acc, scraper=scraper)
            touched.append({"account": acc.pk, "pending": r["pending"],
                            "ingested": r["ingested"], "failed": r["failed"]})
            if r["pending"] and not r["ingested"]:
                # 补不动的缺口（例：官方个人历史列出的场次被本站 rated 规则判为
                # 非 rated）每天都会被重新扫到，必须显式报出来，否则既浪费预算
                # 又永远看不出「已收敛」
                still_pending.append({"account": acc.pk, "pending": r["pending"]})
        except Exception:  # noqa: BLE001 - 单账号异常不影响其余账号
            logger.exception("牛客历史巡检失败 account=%s", acc.pk)

    if still_pending:
        logger.warning("牛客历史巡检：以下账号的缺口本次未补上（多为 rated 口径差异）: %s",
                       still_pending)
    if drift:
        logger.warning("牛客历史巡检：%s 个账号与官方主页数据有差异（仅告警不改库）: %s",
                       len(drift), drift[:8])
    else:
        logger.info("牛客历史巡检：与官方主页对账无差异（已比对 %s 个账号）", checked)
    if any(t["ingested"] for t in touched):
        logger.info("牛客历史巡检完成: %s", touched)
        if _broker_reachable():
            try:
                from apps.ranking.tasks import recompute_ranking_task
                recompute_ranking_task.delay()
            except Exception as exc:  # noqa: BLE001
                logger.warning("巡检补数后重算派发失败: %s", exc)
    else:
        logger.info("牛客历史巡检：本次无新入库场次，跳过积分重算")
    return {"accounts": touched, "still_pending": still_pending,
            "drift": drift, "checked": checked}


def dispatch_account_history_backfill(platform_account_id):
    """绑定/换绑成功后派发定向补数任务；派发失败只影响时效（有每日巡检兜底）。

    先探 broker 再发布，和 _dispatch_crawl 同理：本沙箱连未监听的 Redis 是黑洞
    而非 refused，在请求线程里直接 .delay() 会把绑定接口卡住几十秒。
    """
    def _run():
        if not _broker_reachable():
            logger.warning("消息队列不可达，牛客定向补数交由每日巡检兜底 account=%s",
                           platform_account_id)
            return
        try:
            backfill_account_history_task.delay(platform_account_id)
        except Exception:  # noqa: BLE001 - 派发失败只影响时效
            logger.warning("牛客定向补数派发失败 account=%s",
                           platform_account_id, exc_info=True)

    threading.Thread(target=_run, name=f"nc-backfill-{platform_account_id}",
                     daemon=True).start()


@shared_task(bind=True)
def crawl_codeforces(self, job_id=None, count=20, mode="rating", force=False):
    params = {"count": count, "mode": mode}
    if force:
        params["force"] = True
    job = _get_or_create_job(job_id, Platform.CODEFORCES, self.request.id, params)

    def worker():
        s = _load_scraper(Platform.CODEFORCES)
        all_contests = s.parse_contests(s.fetch_contests())
        # contest.list 按 id 降序（最新在前）。先本地筛掉未结束比赛（不联网），
        # 只对最近的 FINISHED 窗口做 rated 判定——否则 filter_contests 会
        # 对全量历史逐条联网 ratingChanges，CF 2.1s 限速下冷启动需数十分钟。
        recent_finished = [c for c in all_contests
                           if c.get("phase") == "FINISHED"][:count * 2]
        recent = s.filter_contests(recent_finished, rated_only=True,
                                   exclude_paid=False)[:count]
        # A：预筛 = 窗口 ∪ 索引历史。用户历史比赛（可能很早，如 contest 2227）
        #    不在「最近窗口」内，若只做窗口∩索引交集会漏掉，导致永远抓不到历史成绩。
        #    force=True 跳过预筛，用于冷启动全量引导。
        if not force:
            relevant = relevant_contest_ids(Platform.CODEFORCES)
            recent_ids = {
                str(c.get("real_contest_id") or c.get("contest_id"))
                for c in recent
            }
            history = [
                c for c in all_contests
                if c.get("phase") == "FINISHED"
                and str(c.get("real_contest_id") or c.get("contest_id")) in relevant
                and str(c.get("real_contest_id") or c.get("contest_id")) not in recent_ids
            ]
            history = s.filter_contests(history, rated_only=True, exclude_paid=False)
            contests = recent + history
        else:
            contests = recent
        cache_dir = _crawler_cache_dir(Platform.CODEFORCES)
        handles = _relevant_handles(Platform.CODEFORCES)  # B：只为本平台用户补齐每题明细
        for c in contests:
            cid = c.get("real_contest_id") or c.get("contest_id")
            yield c, s.scrape_contest_detail(
                cid, mode=mode, handles=handles,
                cache_dir=cache_dir,
                cache_ttl_hours=_contest_cache_ttl(c))

    return _run_job(job, worker)


@shared_task(bind=True)
def crawl_atcoder(self, job_id=None, count=20, force=False):
    params = {"count": count}
    if force:
        params["force"] = True
    job = _get_or_create_job(job_id, Platform.ATCODER, self.request.id, params)

    def worker():
        s = _load_scraper(Platform.ATCODER)
        all_contests = s.parse_contests(s.fetch_contests())
        # kenkoooo contests.json 的原始顺序是**字母序**（APG4b -> ... -> zone2021），
        # 不是时间序！之前 reversed() 取到的是「字母序最靠后」的旧比赛（zone2021 等），
        # 导致抓不到最新的 abc4xx。必须按开始时间降序取最近窗口。
        all_contests.sort(key=lambda c: c.get("start_time") or "", reverse=True)
        # filter 是纯本地（读 rate_change），先取宽窗口再筛
        recent = s.filter_contests(
            all_contests[:count * 2], rated_only=True, exclude_paid=False)[:count]
        # A：预筛 = 窗口 ∪ 索引历史（用户历史比赛即使不在最近窗口也要抓）
        if not force:
            relevant = relevant_contest_ids(Platform.ATCODER)
            recent_ids = {str(c.get("contest_id")) for c in recent}
            history = [
                c for c in all_contests
                if str(c.get("contest_id")) in relevant
                and str(c.get("contest_id")) not in recent_ids
            ]
            history = s.filter_contests(history, rated_only=True, exclude_paid=False)
            # 已入库且无新用户的历史场剪掉，避免索引增长后每轮全量重放
            history = _prune_ingested_history(Platform.ATCODER, history)
            contests = recent + history
        else:
            contests = recent
        cache_dir = _crawler_cache_dir(Platform.ATCODER)
        for c in contests:
            cid = c.get("contest_id")
            yield c, s.scrape_contest_detail(
                cid, cache_dir=cache_dir,
                cache_ttl_hours=_contest_cache_ttl(c))

    return _run_job(job, worker)


@shared_task(bind=True, soft_time_limit=60 * 55, time_limit=60 * 60)
def crawl_nowcoder(self, job_id=None, months=None, months_back=None, force=False):
    """牛客最慢（1100 人约 65s），路由到 crawl_slow 队列。

    软超时单独放宽到 55 分钟：牛客「窗口∪索引历史」可能一次要抓几十场
    （每场 65s~数分钟），全局 25 分钟软超时会让任务反复 SoftTimeLimitExceeded
    只抓一半。time_limit 60 分钟留收尾余量，防止任务卡死占死 worker。

    months: 显式指定 ["YYYY-MM", ...]；
    months_back: 自动取最近 N 个月（与 months 互斥，months 优先）；
    都不传则只抓当前月。
    force: True 时跳过「只抓有已关联平台ID用户参与的比赛」预筛（冷启动全量引导）。
    """
    params = {"months": months, "months_back": months_back}
    if force:
        params["force"] = True
    job = _get_or_create_job(job_id, Platform.NOWCODER, self.request.id, params)

    def worker():
        s = _load_scraper(Platform.NOWCODER)
        s.init_session()
        if months:
            base_months = list(months)
        elif months_back:
            base_months = _last_n_months(months_back)
        else:
            base_months = [timezone.now().strftime("%Y-%m")]

        # A：预筛 = 窗口 ∪ 索引历史。
        #    牛客没有「整月全量」外的廉价全量列表，故先按窗口月份 fetch；
        #    若索引（relevant）里有更早的历史比赛，通过个人主页参赛记录 +
        #    rating-history 反查其所在月份并扩展抓取范围，避免用户历史成绩永远抓不到。
        #    两个源都要看：主页列表是超集，rating-history 不列的场次（如平台对该
        #    用户取消计分的周赛）只在前者里有时间戳。
        relevant = set() if force else relevant_contest_ids(Platform.NOWCODER)
        target = set(base_months)
        if relevant:
            for acc in PlatformAccount.objects.filter(platform=Platform.NOWCODER):
                # 逐账号兜异常：一个账号的历史接口被拦/超时，不能连带
                # 丢掉后面所有账号的历史月份（历史月份缺失=该用户历史成绩永久抓不到）
                try:
                    stamps = [(str(r.get("contestId")), r.get("time"))
                              for r in s.user_rating_history(acc.handle)]
                    joined = s.contest_joined_history(acc.handle) or {}
                    stamps += [(str(r.get("contestId")), r.get("startTime"))
                               for r in joined.get("rows") or []]
                    for cid, t in stamps:
                        if cid in relevant and t:
                            ym = datetime.fromtimestamp(
                                t / 1000).strftime("%Y-%m")
                            target.add(ym)
                except Exception as exc:  # noqa: BLE001 - 单账号失败不阻断其余账号
                    logger.warning("牛客历史月份反查失败（handle=%s）: %s",
                                   acc.handle, exc)

        contests = []
        for ym in sorted(target):
            contests.extend(s.parse_contests(s.fetch_contests(ym)))
        # B：先把「窗口月份内 ∪ 索引里」的比赛预筛出来（纯本地、不联网），
        #    再交给 filter_contests 逐场判定 rated/付费。否则历史月份扩展后
        #    会对数百场校赛/非 rated 赛逐个请求 contest-info，白白耗时十几分钟。
        if not force and relevant:
            base = set(base_months)

            def _ym_of(c):
                return (c.get("start_time") or "")[:7]

            contests = [
                c for c in contests
                if str(c.get("real_contest_id") or c.get("contest_id")) in relevant
                or _ym_of(c) in base
            ]
        contests = s.filter_contests(contests, rated_only=True, exclude_paid=False)

        # C0：只处理已结束的比赛。进行中/未开始的比赛榜单不完整、rating 未定，
        #    入库会产生脏数据且落盘缓存一周内不会自愈（CF 侧有 phase=FINISHED
        #    过滤；牛客日历无 phase 字段，按 endTime 对齐）。
        def _ended(c):
            dt = _contest_end_dt(c)
            return True if dt is None else dt <= timezone.now()

        contests = [c for c in contests if _ended(c)]

        # C：单次场数上限只约束「窗口内比赛」，防止比赛密集月一轮抓不完
        #    （2026-08 牛客单月超 50 场 rated）。⚠️ 截断前必须按开始时间
        #    降序——contests 按月份升序拼接，直接切片会砍掉尾部「最新的
        #    比赛」（曾致 2026-08 练习赛 156 永远进不了处理列表）。
        #    窗口外的「索引历史比赛」（绑定用户索引带出的）不设上限：
        #    已入库且无新用户的历史场被 _prune_ingested_history 剪掉，
        #    剩余未入库/待补行的场次靠落盘缓存 + 幂等入库跨轮收敛——
        #    否则最老的历史比赛（如 2025-10 的 Round 114）会被截断线
        #    永久挡住，新绑定用户的历史成绩永远补不上（2026-09 缺口根因）。
        contests.sort(key=lambda c: c.get("start_time") or "", reverse=True)
        base_set = set(base_months)
        recent = [
            c for c in contests
            if (c.get("start_time") or "")[:7] in base_set
        ][:50]
        history = _prune_ingested_history(
            Platform.NOWCODER,
            [c for c in contests
             if (c.get("start_time") or "")[:7] not in base_set],
        )
        contests = recent + history
        cache_dir = _crawler_cache_dir(Platform.NOWCODER)
        for c in contests:
            rid = c.get("real_contest_id")
            if not rid:
                continue
            # exclude_cheaters=False：保留作弊记录进入 ingest，
            # 由入库层打排除标记，保证有据可查
            yield c, s.scrape_contest_detail(
                rid, filter_post_contest=True, exclude_cheaters=False,
                cache_dir=cache_dir,
                cache_ttl_hours=_contest_cache_ttl(c))

    return _run_job(job, worker)


def _calendar_atcoder_ratings():
    """AtCoder 未开赛场次的计分区间：官方 /contests/ 页表格。失败只影响 rated 列。

    不用 kenkoooo：它的 contests.json 只收已结束比赛，未开赛的 Rated Range
    在官方页上（"All" / "- ~ 1999" / "-"），与站内 `rate_change` 同口径。
    """
    try:
        return _load_scraper(Platform.ATCODER).fetch_upcoming_ratings() or {}
    except Exception as exc:  # noqa: BLE001 - 排期照落，只是这轮判不出 rated
        logger.warning("日历 rated 富化：AtCoder 官方页取数失败 %s", exc)
        return None


def _calendar_nowcoder_flags(eid, scraper):
    """牛客未开赛场次：contest-info 的 category+uid+needCharge，未开赛即可判。
    判不出（接口不可用）返回 None，调用方按「未判定」处理。"""
    try:
        flags = scraper.check_rated({"real_contest_id": eid})
    except Exception as exc:  # noqa: BLE001
        logger.warning("日历 rated 富化：牛客 %s 判定失败 %s", eid, exc)
        return None
    return flags if flags.get("is_rated") is not None else None


def _annotate_calendar_rated(rows):
    """给排期行补「平台是否计分」，就地写 is_rated / rated_comment，返回统计。

    为什么必须补：日历行原先一律 is_rated=False —— 那是在替一场还没开始的比赛
    宣布「不计分」，而日历的 Rated 筛选读的正是这一列，未开赛场次因此整排被滤空
    （2026-09-24 线上实测：25 条排期行 25 条 is_rated=false）。
    is_rated 在这里只是展示口径：积分链路由 `rated_source` 上的日历标记挡住
    （见 contests.models.countable），赛后正常爬取会用平台自己的判定覆盖整行。
    """
    from clist_scraper import preview_codeforces_rated

    by_platform = {r.get("platform") for r in rows}
    at_map = (_calendar_atcoder_ratings()
              if Platform.ATCODER in by_platform else {})
    nc_scraper = None
    if Platform.NOWCODER in by_platform:
        try:
            nc_scraper = _load_scraper(Platform.NOWCODER)
        except Exception as exc:  # noqa: BLE001
            logger.warning("日历 rated 富化：牛客客户端起不来 %s", exc)

    stat = {"rated": 0, "unrated": 0, "unknown": 0}
    for r in rows:
        eid = str(r.get("real_contest_id") or r.get("contest_id") or "")
        platform = r.get("platform")
        rated, note = None, ""
        if platform == Platform.ATCODER:
            info = (at_map or {}).get(eid)
            if info is None:
                note = "官方页未列出该场，计分区间待赛后确认"
            else:
                rated = bool(info["rated"])
                note = f"官方 Rated Range={info.get('range') or '(空)'}"
                # clist 偶尔给不出 event 名（回退成 id），官方页的名字更可靠
                if (not r.get("name") or r["name"] == eid) and info.get("name"):
                    r["name"] = str(info["name"])[:255]
        elif platform == Platform.NOWCODER:
            flags = _calendar_nowcoder_flags(eid, nc_scraper) if nc_scraper else None
            if flags:
                rated = bool(flags.get("is_rated"))
                r["is_paid"] = bool(flags.get("is_paid"))
                if flags.get("series"):
                    r["series"] = str(flags["series"])[:100]
                note = str(flags.get("rated_comment") or "")[:200]
            else:
                note = "详情接口未取到，计分判定待赛后"
        elif platform == Platform.CODEFORCES:
            rated = preview_codeforces_rated(r.get("name"))
            note = ("按官方命名预判：" + ("计分系列" if rated is True else
                                          "不计分名称" if rated is False else
                                          "无计分线索"))
        else:
            note = "该平台无预告期计分判定源"

        r["is_rated"] = bool(rated)
        r["rated_comment"] = note
        stat["rated" if rated else ("unrated" if rated is False else "unknown")] += 1
    logger.info("日历 rated 富化完成: %s", stat)
    return stat


def _load_clist_scraper():
    """clist.by 排期客户端。凭据缺失时直接抛，让调用方记日志而不是静默产出空日历。"""
    from clist_scraper import ClistScraper
    return ClistScraper(settings.CLIST_USERNAME, settings.CLIST_API_KEY)


@shared_task(soft_time_limit=60 * 5, time_limit=60 * 8)
def sync_calendar_contests(days_ahead=None):
    """用 clist.by 的聚合排期刷新站内日历行（未开赛 + 进行中，只建 Contest）。

    为什么换 clist 而不是三个官方源：`contest.list` 与牛客月历只给得出近处排期，
    kenkoooo `contests.json` 实测（2026-09-23）最新一条就是当天、根本不含未来场
    —— 三源凑不出一张能往后翻的月历。clist 一次请求覆盖 20+ 平台，我们按比赛
    URL 反解出站内 `external_id`（与各自爬虫同口径），只认其中三平台，其余平台
    要等 `Platform` 枚举扩了才收。

    为什么必须沉淀成行：既有爬取只消费「已结束」窗口（见 crawl_codeforces 的
    phase=FINISHED 过滤），未开赛场次从不入库 → `status=upcoming` 实测恒为 0。

    只读列表接口，绝不碰 `scrape_contest_detail`：未开始的比赛没有榜单，落了空
    原文会被 `_contest_cache_ttl` 判成 168 小时缓存，反过来把赛后的真成绩挡在门外。
    取数失败保留上一轮的日历行，不把已经渲染好的日历清成空页。
    """
    from apps.crawler.ingest import (_parse_dt, prune_stale_calendar_rows,
                                     upsert_calendar_rows)

    now = timezone.now()
    try:
        scraper = _load_clist_scraper()
    except Exception as exc:  # noqa: BLE001
        # 凭据/依赖缺失是**永久性**故障：和一次上游 503 分开记，否则机器配错
        # 只会每天在 worker 日志里留一行 warning，功能静默停摆。
        logger.error("日历排期同步未启动（凭据或依赖缺失）: %s", exc)
        return {"ok": False, "fatal": True, "error": str(exc)[:200]}

    try:
        rows = scraper.fetch_upcoming(
            days_ahead=days_ahead or settings.CALENDAR_AHEAD_DAYS)
    except Exception as exc:  # noqa: BLE001 - 上游故障不该清空日历
        logger.warning("日历排期同步失败，保留上一轮数据: %s", exc)
        return {"ok": False, "error": str(exc)[:200]}

    grouped = {}
    for r in rows:
        end = _parse_dt(r.get("end_time"))
        if end is None or end <= now:
            continue        # 今天之前就结束了：归正常爬取路径管
        grouped.setdefault(r["platform"], []).append(r)

    pending = [r for rs in grouped.values() for r in rs]
    rated_stat = _annotate_calendar_rated(pending)

    sources = {p: upsert_calendar_rows(p, rs, now=now) for p, rs in grouped.items()}
    written = sum(s["created"] + s["updated"] for s in sources.values())
    if rows and not written:
        # 上游给数正常、站内一行没落 → 八成是对方改了字段口径，必须喊出来
        logger.warning("clist 给了 %s 场却零行落库，样本: %s", len(rows), rows[:2])
    pruned = prune_stale_calendar_rows(days=settings.CALENDAR_PRUNE_AFTER_DAYS,
                                       now=now)
    logger.info("日历排期同步完成: %s（清理过期行 %s 条）", sources, pruned)
    return {"ok": True, "fetched": len(rows), "sources": sources,
            "rated": rated_stat, "pruned": pruned}


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
