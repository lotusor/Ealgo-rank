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

    if not force and (not is_rated or is_paid):
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

    for r, handle, display_name, is_cheater, raw_display in prepared:
        account = account_map.get(handle.lower())
        is_post = bool(r.get("post_contest_append"))

        if is_cheater:
            cheaters += 1
        if account:
            matched += 1

        # 与我们无关且不是作弊证据的记录直接丢弃
        if account is None and not is_cheater:
            continue

        if is_cheater:
            excluded, reason = True, ExcludeReason.CHEATER
        elif is_post:
            excluded, reason = True, ExcludeReason.POST_CONTEST
        elif account is None:
            excluded, reason = True, ExcludeReason.UNBOUND
        else:
            excluded, reason = False, ""

        if not excluded:
            countable += 1

        extra = r.get("extra") or {}
        Participation.objects.update_or_create(
            contest=contest,
            handle_lower=handle.lower(),
            defaults={
                "platform_account": account,
                "handle": handle[:100],
                "display_name": display_name[:150],
                "raw_display_name": (raw_display or "")[:200],
                "rank": r.get("rank"),
                "solved_count": r.get("accepted_count"),
                "total_score": r.get("total_score"),
                "penalty_ms": r.get("penalty_time_ms"),
                "rating_delta": extra.get("delta"),
                "old_rating": extra.get("old_rating"),
                "new_rating": extra.get("new_rating"),
                "is_excluded": excluded,
                "exclude_reason": reason,
                "score_detail": r.get("score_detail") or [],
                "extra": extra,
            },
        )

    return {"total": total, "cheaters": cheaters,
            "matched": matched, "countable": countable}


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
