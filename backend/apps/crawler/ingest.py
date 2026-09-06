"""
爬虫产出 -> 数据库的入库层。

三条硬规则，全部在这里落地，不依赖调用方自觉：
  1. 只入 rated 且非付费的比赛（contest.is_rated and not is_paid）
  2. 牛客平台标记的作弊账号（userName 前缀「已被标记为作弊」）落库但强制
     is_excluded=True，不进积分
  3. 学校归属只认 PlatformAccount 绑定，绝不读榜单里的 school/organization/affiliation
"""

import logging
import re
from datetime import datetime, timezone as dt_timezone

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import PlatformAccount
from apps.common.models import ExcludeReason, Platform
from apps.contests.models import Contest, Participation, Problem
from apps.schools.models import AtCoderAffiliationAlias, normalize_atcoder_affiliation

logger = logging.getLogger(__name__)

# 与 crawlers/nowcoder_scraper.py 的 CHEATER_PATTERN 保持一致。
# 两处都要有：爬虫层负责打标记，入库层负责兜底 —— 万一读到的是旧版本
# 爬虫产出的 JSON（没有 is_cheater 字段），这里仍能识别出来。
CHEATER_PATTERN = re.compile(
    r"^\s*[\[\【\(\（]\s*(?:该用户)?已?被?(?:平台)?标记为作弊[^\]\】\)\）]*[\]\】\)\）]\s*"
)


def detect_cheater(display_name):
    """返回 (is_cheater, clean_name)。入库层的最后一道防线。"""
    raw = display_name or ""
    m = CHEATER_PATTERN.match(raw)
    if m:
        return True, raw[m.end():].strip()
    return False, raw.strip()


def _parse_dt(value):
    """接受 '2026-08-04 20:00:00' / ISO 串 / 秒级时间戳，返回 aware datetime。"""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=dt_timezone.utc)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            naive = datetime.strptime(str(value)[:19], fmt)
            return timezone.make_aware(naive, timezone.get_default_timezone())
        except ValueError:
            continue
    logger.warning("无法解析时间: %r", value)
    return None


@transaction.atomic
def ingest_contest(platform, contest_meta, detail, *, force=False):
    """
    入库单场比赛及其排名。

    platform      Platform 枚举值
    contest_meta  爬虫 contest_list 里的一条（含 is_rated / is_paid 等判定结果）
    detail        scrape_contest_detail 的返回值（problems / ranks / ...）
    force         True 时即使比赛非 rated 或付费也强制入库（仅供人工排查用）

    返回统计字典。
    """
    is_rated = bool(contest_meta.get("is_rated"))
    is_paid = bool(contest_meta.get("is_paid"))

    # 付费 rated 比赛同样计入（用户决策：只要 rated 就收录并计分），
    # is_paid 仅保留作展示标记，不再作为排除依据。
    if not force and not is_rated:
        logger.info("跳过非计分比赛: %s (rated=%s paid=%s)",
                    contest_meta.get("name"), is_rated, is_paid)
        return {"skipped": True, "reason": "not_countable"}

    external_id = str(contest_meta.get("real_contest_id")
                      or contest_meta.get("contest_id")
                      or contest_meta.get("id"))

    contest, _created = Contest.objects.update_or_create(
        platform=platform,
        external_id=external_id,
        defaults={
            "name": contest_meta.get("name") or external_id,
            "url": contest_meta.get("link") or contest_meta.get("url") or "",
            "start_time": _parse_dt(contest_meta.get("start_time")),
            "end_time": _parse_dt(contest_meta.get("end_time")),
            "duration_minutes": contest_meta.get("duration_minutes"),
            "is_rated": is_rated,
            "is_paid": is_paid,
            "rated_source": (contest_meta.get("rated_source") or "")[:100],
            "rated_comment": (contest_meta.get("rated_comment") or "")[:255],
            "series": (contest_meta.get("series") or "")[:100],
            "raw_meta": contest_meta,
            "crawled_at": timezone.now(),
        },
    )

    _ingest_problems(contest, detail.get("problems") or [])
    stats = _ingest_ranks(contest, platform, detail.get("ranks") or [])

    contest.problem_count = contest.problems.count()
    contest.participant_count = stats["total"]
    contest.valid_participant_count = stats["countable"]
    contest.cheater_count = stats["cheaters"]
    contest.save(update_fields=["problem_count", "participant_count",
                                "valid_participant_count", "cheater_count",
                                "updated_at"])

    logger.info("入库 %s: 榜单 %d 条，作弊 %d 条已排除，绑定学生 %d 条，计分 %d 条",
                contest.name, stats["total"], stats["cheaters"],
                stats["matched"], stats["countable"])
    return {"skipped": False, "contest_id": contest.pk, **stats}


def _ingest_problems(contest, problems):
    for p in problems:
        idx = p.get("index") or p.get("problem") or ""
        if not idx:
            continue
        Problem.objects.update_or_create(
            contest=contest,
            index=str(idx)[:10],
            defaults={
                "title": (p.get("title") or p.get("name") or "")[:255],
                "external_id": str(p.get("problem_id") or "")[:64],
                "full_score": p.get("total_score") or p.get("full_score"),
                "solved_count": p.get("accepted_count") or 0,
                "raw": p,
            },
        )


def _ingest_ranks(contest, platform, ranks):
    """
    写入排名。只对「已绑定学生」或「作弊账号」建记录：
      - 已绑定：这是我们要算分的人
      - 作弊：即便未绑定也留证据，方便管理员核查；已绑定的更要留，用于申诉
    其余无关路人（一场 CF 有一两万人）不落库，否则表会迅速膨胀且毫无价值。
    """
    handles = []
    prepared = []

    for r in ranks:
        raw_name = r.get("user_name") or ""
        # 优先信任爬虫层的判定，同时用本地正则兜底旧数据
        is_cheater = bool(r.get("is_cheater"))
        fallback_cheater, clean_name = detect_cheater(raw_name)
        is_cheater = is_cheater or fallback_cheater
        display_name = clean_name or raw_name

        handle = str(r.get("uid") or r.get("handle") or "").strip()
        if not handle:
            continue
        handles.append(handle.lower())
        prepared.append((r, handle, display_name, is_cheater,
                         (r.get("extra") or {}).get("raw_user_name") or
                         (raw_name if is_cheater else "")))

    # 一次查库拿到所有绑定关系，避免逐条 N+1
    account_map = {
        a.handle_lower: a
        for a in PlatformAccount.objects.filter(
            platform=platform, handle_lower__in=set(handles)
        ).select_related("school")
    }

    total = len(prepared)
    cheaters = 0
    matched = 0
    countable = 0

    # AtCoder affiliation 归一化表（仅参考/核对，不影响归属）；一次性预取避免 N+1
    alias_map = {}
    if platform == Platform.ATCODER:
        alias_map = {
            a.raw_affiliation.strip().lower(): a
            for a in AtCoderAffiliationAlias.objects.filter(is_active=True)
        }

    for r, handle, display_name, is_cheater, raw_display in prepared:
        account = account_map.get(handle.lower())
        is_post = bool(r.get("post_contest_append"))

        if is_cheater:
            cheaters += 1
        if account:
            matched += 1

        # 只落库「已绑定用户」的记录；未绑定的路人一律丢弃——
        # 作弊路人明细同样不落（2026-09-07 用户决策：后台「参赛记录」被 1630 条
        # 路人行淹没，管理成本过高），作弊统计走 Contest.cheater_count 聚合列，
        # 需要明细证据的场景仅限「已绑定用户被标记」（申诉用，照旧保留）。
        if account is None:
            continue

        if is_cheater:
            excluded, reason = True, ExcludeReason.CHEATER
        elif is_post:
            excluded, reason = True, ExcludeReason.POST_CONTEST
        else:
            excluded, reason = False, ""

        if not excluded:
            countable += 1

        extra = dict(r.get("extra") or {})
        # AtCoder affiliation 归一化（仅供参考/核对，不参与归属）
        if alias_map and extra.get("affiliation"):
            norm = normalize_atcoder_affiliation(extra["affiliation"], alias_map)
            if norm:
                extra["affiliation_normalized"] = norm
        # rating 涨落：CF 爬虫在 extra 里直接给 delta，AtCoder 只给 old/new，
        # 牛客榜单两者皆无（由 backfill_nowcoder_ratings 事后从 rating-history 补）。
        # 这里统一兜底：有 old/new 就推导 delta，保证三平台契约一致。
        old_rating = extra.get("old_rating")
        new_rating = extra.get("new_rating")
        delta = extra.get("delta")
        if delta is None and old_rating is not None and new_rating is not None:
            delta = new_rating - old_rating
        defaults = {
            "platform_account": account,
            "handle": handle[:100],
            "display_name": display_name[:150],
            "raw_display_name": (raw_display or "")[:200],
            "rank": r.get("rank"),
            "solved_count": r.get("accepted_count"),
            "total_score": r.get("total_score"),
            "penalty_ms": r.get("penalty_time_ms"),
            "is_excluded": excluded,
            "exclude_reason": reason,
            "score_detail": r.get("score_detail") or [],
            "extra": extra,
        }
        # rating 涨落仅当数据源提供时写入；None 不覆盖已有值——牛客榜单本身
        # 不含 rating（事后由 rating-history 回填），若用 None 覆盖，回填一次
        # 静默失败（接口被拦/返回空）就会清掉已有 rating（2026-09-03 实测）。
        if delta is not None:
            defaults["rating_delta"] = delta
        if old_rating is not None:
            defaults["old_rating"] = old_rating
        if new_rating is not None:
            defaults["new_rating"] = new_rating
        Participation.objects.update_or_create(
            contest=contest,
            handle_lower=handle.lower(),
            defaults=defaults,
        )

    # 增量维护「参与比赛索引」：把本场 contest.external_id 记入每位命中账号，
    # 供爬虫下次预筛（只抓有已关联平台ID用户参与的比赛）。未绑定的路人账号不记入。
    if matched:
        updates = {}
        for r, handle, _display_name, _is_cheater, _raw in prepared:
            account = account_map.get(handle.lower())
            if account is not None:
                updates.setdefault(account.id, set()).add(contest.external_id)
        if updates:
            accs = PlatformAccount.objects.in_bulk(updates.keys())
            for aid, ext_ids in updates.items():
                acc = accs.get(aid)
                if acc is None:
                    continue
                merged = set(acc.participated_contests or []) | ext_ids
                acc.participated_contests = list(merged)
                acc.save(update_fields=["participated_contests", "updated_at"])

    return {"total": total, "cheaters": cheaters,
            "matched": matched, "countable": countable}


def backfill_nowcoder_ratings():
    """从牛客 rating-history 接口回填参赛记录的 rating 涨落。

    牛客榜单（real-time-rank-data）不含 rating 涨落字段，只有官方个人历史
    接口 `acm/contest/rating-history?uid=` 返回每场的 rating（赛后）与
    changeValue（涨落）。按 contest.external_id 匹配回填，让牛客的
    rating_delta / old_rating / new_rating 与 CF/AtCoder 对齐。

    返回回填条数。
    """
    _crawler_dir()
    from nowcoder_scraper import NowCoderScraper

    scraper = NowCoderScraper()
    scraper.init_session()

    updated = 0
    for acc in PlatformAccount.objects.filter(platform=Platform.NOWCODER):
        try:
            hist = scraper.user_rating_history(acc.handle)
        except Exception:  # noqa: BLE001 - 单账号失败不阻断整体
            logger.exception("牛客 rating 回填：账号 %s 历史拉取失败", acc.handle)
            continue
        by_contest = {
            str(x.get("contestId")): x
            for x in hist if x.get("contestId") not in (None, "")
        }
        qs = Participation.objects.filter(
            platform_account=acc,
            contest__platform=Platform.NOWCODER,
        )
        for p in qs:
            row = by_contest.get(p.contest.external_id)
            if not row:
                continue
            new_rating = row.get("rating")
            delta = row.get("changeValue")
            if new_rating is None and delta is None:
                continue
            old_rating = None
            if new_rating is not None and delta is not None:
                old_rating = new_rating - delta
            changed = False
            if new_rating is not None and p.new_rating != new_rating:
                p.new_rating = new_rating
                changed = True
            if delta is not None and p.rating_delta != delta:
                p.rating_delta = delta
                changed = True
            if old_rating is not None and p.old_rating != old_rating:
                p.old_rating = old_rating
                changed = True
            if changed:
                p.save(update_fields=["old_rating", "new_rating",
                                      "rating_delta", "updated_at"])
                updated += 1
    if updated == 0:
        # 静默零更新 = 接口被拦/返回空的典型征兆（2026-09-03 事故：回填空跑
        # 后榜单重爬把已有 rating 覆盖为 None）。必须显式暴露供巡检发现。
        logger.warning(
            "牛客 rating 回填更新 0 条——请检查 rating-history 接口是否被反爬拦截")
    logger.info("牛客 rating 回填完成，更新 %d 条", updated)
    return updated


def rebind_unbound_participations(platform_account):
    """
    学生新绑定平台账号时调用：把历史上以该 handle 出现、当时无人认领的
    参赛记录回填给他。作弊记录不解除排除标记。
    """
    qs = Participation.objects.filter(
        platform_account__isnull=True,
        handle_lower=platform_account.handle_lower,
        contest__platform=platform_account.platform,
    ).exclude(exclude_reason=ExcludeReason.CHEATER)

    updated = 0
    for p in qs:
        p.platform_account = platform_account
        if p.exclude_reason == ExcludeReason.UNBOUND:
            p.is_excluded = False
            p.exclude_reason = ""
        p.save(update_fields=["platform_account", "is_excluded",
                              "exclude_reason", "updated_at"])
        updated += 1
    logger.info("回填 %s 的历史记录 %d 条", platform_account, updated)
    return updated


def _crawler_dir():
    """返回爬虫脚本目录并加入 sys.path（与 tasks.py 同一约定）。"""
    import os
    import sys
    from django.conf import settings
    base = str(getattr(settings, "CRAWLER_DIR", None) or "")
    if base and base not in sys.path:
        sys.path.insert(0, base)
    return base


def fill_participated_contests(platform_account):
    """按官方个人历史接口补全单个 PlatformAccount 的参与比赛索引。

    Codeforces -> user.rating（contestId 列表）
    AtCoder    -> users/{handle}/history/json（ContestScreenName 列表）
    牛客       -> acm/contest/rating-history?uid=（contestId 列表，即 real_contest_id）

    返回 (updated: bool, ids_count: int)。索引为空时也算一次更新写入。
    """
    if not platform_account.handle:
        return False, 0

    # 确保爬虫脚本目录在 sys.path（backend gunicorn 进程未必加载过 tasks.py，
    # 直接 from cf_scraper/atcoder_scraper/nowcoder_scraper 会 ImportError）
    _crawler_dir()

    ids = []
    if platform_account.platform == Platform.CODEFORCES:
        from cf_scraper import CodeforcesScraper
        ids = CodeforcesScraper().user_rating_contest_ids(platform_account.handle)
    elif platform_account.platform == Platform.ATCODER:
        from atcoder_scraper import AtCoderScraper
        ids = AtCoderScraper().user_history_contest_ids(platform_account.handle)
    elif platform_account.platform == Platform.NOWCODER:
        from nowcoder_scraper import NowCoderScraper
        scraper = NowCoderScraper()
        scraper.init_session()
        ids = scraper.user_rating_history_contest_ids(platform_account.handle)
    else:
        return False, 0

    ids = [str(x) for x in ids if x not in (None, "")]
    merged = sorted(set(platform_account.participated_contests or []) | set(ids))
    if merged != list(platform_account.participated_contests or []):
        platform_account.participated_contests = merged
        platform_account.save(update_fields=["participated_contests", "updated_at"])
        return True, len(ids)
    return False, len(ids)


def fill_participated_contests_async(platform_account_id):
    """后台线程补全参与比赛索引（绑定接口即时返回，不阻塞用户）。

    失败不抛出，仅记录日志；CF/AT 限速决定单账号耗时约 1~5s。
    """
    import threading
    from django.db import connection

    def _run():
        try:
            # 线程内关闭旧连接，避免复用父线程的 SQLite/PG 连接造成状态污染
            connection.close()
            acc = PlatformAccount.objects.get(pk=platform_account_id)
            updated, n = fill_participated_contests(acc)
            logger.info("异步补全 %s 参与比赛索引: 官方接口返回 %d 场, 更新=%s",
                        acc, n, updated)
        except Exception:  # noqa: BLE001 - 后台线程不得抛出到调用方
            logger.exception("异步补全参与比赛索引失败 (account_id=%s)",
                             platform_account_id)
        finally:
            connection.close()

    threading.Thread(target=_run, daemon=True,
                     name=f"fill-idx-{platform_account_id}").start()

