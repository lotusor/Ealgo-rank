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


def backfill_nowcoder_ratings(account_ids=None):
    """从牛客 rating-history 接口回填参赛记录的 rating 涨落。

    牛客榜单（real-time-rank-data）不含 rating 涨落字段，只有官方个人历史
    接口 `acm/contest/rating-history?uid=` 返回每场的 rating（赛后）与
    changeValue（涨落）。按 contest.external_id 匹配回填，让牛客的
    rating_delta / old_rating / new_rating 与 CF/AtCoder 对齐。

    account_ids 给定时只回填这些 PlatformAccount（新绑定账号定向补数）。
    返回 {"updated", "accounts", "empty_history", "failed"}：逐账号留痕，
    只有全局 0 更新才告警是不够的 —— 个别账号被反爬拦掉时其余账号仍有更新，
    整体看起来"成功"，缺的那部分却永远没人知道（2026-09-22 实测漏 26 条）。
    """
    _crawler_dir()
    from nowcoder_scraper import NowCoderScraper

    scraper = NowCoderScraper()
    scraper.init_session()

    qs = PlatformAccount.objects.filter(platform=Platform.NOWCODER)
    if account_ids:
        qs = qs.filter(pk__in=account_ids)

    updated = 0
    empty_history = []
    failed = []
    for acc in qs:
        try:
            hist = scraper.user_rating_history(acc.handle)
        except Exception:  # noqa: BLE001 - 单账号失败不阻断整体
            logger.exception("牛客 rating 回填：账号 %s 历史拉取失败", acc.handle)
            failed.append(acc.pk)
            continue
        if not hist:
            # 接口返回空 = 被拦的典型征兆（账号明明有参赛记录却零行）
            empty_history.append(acc.pk)
            logger.warning("牛客 rating 回填：账号 %s（user=%s）官方历史返回 0 行，"
                           "疑似被反爬拦截", acc.handle, acc.user_id)
            continue
        by_contest = {
            str(x.get("contestId")): x
            for x in hist if x.get("contestId") not in (None, "")
        }
        n_acc = 0
        for p in Participation.objects.filter(
            platform_account=acc,
            contest__platform=Platform.NOWCODER,
        ):
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
                n_acc += 1
        # 有官方历史、有参赛行，却一行都没补上：external_id 对不上或涨落早已有值
        if n_acc == 0 and Participation.objects.filter(
                platform_account=acc,
                contest__platform=Platform.NOWCODER).exists():
            logger.info("牛客 rating 回填：账号 %s 本次零更新（涨落已齐或场次对不上）",
                        acc.handle)

    result = {"updated": updated, "accounts": qs.count(),
              "empty_history": empty_history, "failed": failed}
    if updated == 0 and qs.count() and \
            len(failed) + len(empty_history) == qs.count():
        # 零更新且所有账号都没取到数据 = 接口被拦的确定性征兆
        # （旧实现只看全局零更新，把"没什么可补"的正常情况也报成告警，
        #   噪声太大反而盖掉真信号）
        logger.warning(
            "牛客 rating 回填更新 0 条、%d 个账号全部失败/空返回"
            "——请检查 rating-history 接口是否被反爬拦截", qs.count())
    logger.info("牛客 rating 回填完成 %s", result)
    return result


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


def missing_nowcoder_contest_ids(account):
    """该牛客账号「官方索引里有、站内却没有参赛行」的比赛 external_id。

    判定口径是 (账号, 比赛) 这一行在不在，而不是比赛在不在 —— 新绑定用户的
    历史缺失几乎都属于「比赛早就入库、只缺他这一行」（2026-09-22 实测：
    学生榜第一名 21 场缺失里 20 场的 Contest 早已在库）。只按「比赛未入库」
    筛选的旧补抓命令因此永远修不掉这类缺口。
    """
    idx = {str(x) for x in (account.participated_contests or [])}
    if not idx:
        return set()
    have = set(Participation.objects.filter(
        platform_account=account,
        contest__platform=Platform.NOWCODER,
    ).values_list("contest__external_id", flat=True))
    return idx - have


# 牛客主页参赛记录行里「该场对该用户计入了 rating 体系」的标记值。
# ratingStatus = 本场对**该用户**是否计分；originRatingStatus = **该比赛**本身是否 rated。
NOWCODER_RATED_FLAG = "FINISHED"


def _joined_flag(row, key):
    return str(row.get(key) or "").upper()


def _joined_is_rated(row):
    return NOWCODER_RATED_FLAG in (_joined_flag(row, "originRatingStatus"),
                                   _joined_flag(row, "ratingStatus"))


def _as_int(value):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


# 牛客把「作弊罚分」做成一张名为「比赛违规」的伪赛次（contestId 11052 类：
# category=10、起止只差 5 分钟、无榜单、contest-info 直接报 1001），它只出现在
# rating-history 折线源里，个人主页参赛记录列表**不含**它。收进索引就会变成一个
# 永远补不出行的假缺口，每天吃掉一份巡检预算并淹没真缺口告警。
VIOLATION_NAME_RE = re.compile("违规")


def rating_history_index_ids(rows):
    """rating-history 行 → (可进索引的 contestId, 识别出的伪赛次 contestId)。

    只按名称正向识别伪赛次，不用「不在主页列表里」反推 —— 按平台规则，真比赛
    也可能因整场取消成绩而从参赛记录列表消失，反推会把这类已知场次误删。
    """
    ids, violations = set(), set()
    for row in rows or []:
        cid = row.get("contestId") if isinstance(row, dict) else None
        if cid in (None, ""):
            continue
        name = str(row.get("contestName") or "")
        (violations if VIOLATION_NAME_RE.search(name) else ids).add(str(cid))
    return ids, violations


def joined_index_contest_ids(rows):
    """个人主页参赛行 → 该并进「参赛索引」的 contestId 集合。

    只收任一 rating 标记为 FINISHED 的行。两个标记全 NO 的是校内赛/同步赛，本站
    对不计分场次不落参赛行（补数循环里就是那句「非 rated 跳过」），把它们收进索引
    会造出**永远补不动的缺口**，把每日巡检的账号预算吃光、并淹没真缺口告警。
    这类场次由 compare_nowcoder_history 单独报成 unrated_rows，留给展示补全。
    """
    return {str(r.get("contestId")) for r in (rows or [])
            if r.get("contestId") not in (None, "") and _joined_is_rated(r)}


def compare_nowcoder_history(account, rows, *, min_rank_diff=5):
    """逐行比对官方主页数据与站内 (账号,比赛) 行；只报差异，不改数据。

    为什么不改：榜单是同一场比赛所有账号共同的来源，为对齐官方数字单改一行会
    破坏同场一致性；而且 2026-09-22 实测的那处名次差异（4082 vs 4111）源于官方
    榜单在两次抓取之间又进了人，属陈旧度而非抓错。校验的价值是把这类漂移和
    「涨落整列 NULL」式的停摆变成每天自动看得见的事。
    """
    out = {"checked": 0, "missing_rows": [], "rank_diff": [],
           "delta_diff": [], "ac_diff": [], "unrated_rows": []}
    if not rows:
        return out
    mine = {p.contest.external_id: p for p in Participation.objects.filter(
        platform_account=account,
        contest__platform=Platform.NOWCODER,
    ).select_related("contest")}
    for row in rows:
        cid = str(row.get("contestId") or "")
        if not cid:
            continue
        rated = _joined_is_rated(row)
        brief = {"contestId": cid, "rank": _as_int(row.get("rank")),
                 "contestName": row.get("contestName")}
        p = mine.get(cid)
        if p is None:
            out["missing_rows" if rated else "unrated_rows"].append(brief)
            continue
        out["checked"] += 1
        official_rank = _as_int(row.get("rank"))
        if p.rank is not None and official_rank is not None and p.rank != official_rank:
            out["rank_diff"].append({**brief, "site": p.rank,
                                     "diff": official_rank - p.rank})
        if rated:  # 不计分场次官方给的是占位 0，与站内 None 不算差异
            official_delta = _as_int(row.get("changeValue"))
            if p.rating_delta is not None and official_delta is not None \
                    and p.rating_delta != official_delta:
                out["delta_diff"].append({**brief, "site": p.rating_delta,
                                          "official": official_delta})
        official_ac = _as_int(row.get("acceptedCount"))
        if p.solved_count is not None and official_ac is not None \
                and p.solved_count != official_ac:
            out["ac_diff"].append({**brief, "site": p.solved_count,
                                   "official": official_ac})
    out["rank_diff"] = [d for d in out["rank_diff"] if abs(d["diff"]) >= min_rank_diff]
    for key in ("missing_rows", "rank_diff", "delta_diff", "ac_diff"):
        if out[key]:
            logger.warning("牛客主页对账 account=%s(%s) %s=%s 处: %s",
                           account.handle, account.pk, key, len(out[key]),
                           out[key][:5])
    return out


# 个人主页来源标记：既是锚点赛次的识别依据（公共比赛列表按它排除），也写进
# Participation.extra，用于区分「榜单来的」与「主页来的」。
PROFILE_SOURCE = "profile_joined"
# 排除条件必须落在非空列上：JSONField 键查找在 SQLite 下会让「没有这个键」的行
# 参与 NOT 运算后得到 NULL，三值逻辑把全部行一起排除掉（实测列表返回 0 行）。
PROFILE_RATED_SOURCE = "profile-joined-history"


def _ts_to_dt(ms):
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=dt_timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def materialize_profile_rows(account, rows, *, log=None):
    """把「官方不计 Rating、但确有其场」的主页行落库，只服务参赛记录展示。

    为什么可以这样做：积分引擎唯一入口 `Participation.objects.countable()` 要求
    `contest.is_rated=True`，而这些锚点赛次一律 is_rated=False，所以既不进积分、
    也不进「参赛场次」统计，纯展示。锚点 Contest 带 `raw_meta.source=profile_joined`
    标记，公共比赛列表默认排除它，避免校内赛/同步赛混进「比赛列表」和难度系数页。

    已存在的赛次若是 rated（例：平台对该用户取消计分的周赛），交回榜单正常补数
    路径处理，这里不建半成品行。
    """
    log = log or (lambda msg: None)
    created = skipped = 0
    mine = {p.contest.external_id for p in Participation.objects.filter(
        platform_account=account,
        contest__platform=Platform.NOWCODER,
    ).select_related("contest")}
    for row in rows or []:
        cid = str(row.get("contestId") or "")
        if not cid:
            continue
        if _joined_is_rated(row) or cid in mine:
            skipped += 1          # 计分层交给榜单补数路径；已有行不重复建
            continue
        rank = _as_int(row.get("rank"))
        if rank is None:
            skipped += 1           # 无名次 = 没有可展示的成绩
            continue
        setting = row.get("settingInfo") or {}
        start, end = _ts_to_dt(row.get("startTime")), _ts_to_dt(row.get("endTime"))
        contest = Contest.objects.filter(platform=Platform.NOWCODER,
                                         external_id=cid).first()
        if contest is None:
            contest = Contest.objects.create(
                platform=Platform.NOWCODER, external_id=cid,
                name=str(row.get("contestName") or cid)[:255],
                url=f"https://ac.nowcoder.com/acm/contest/{cid}",
                start_time=start, end_time=end,
                duration_minutes=(int((end - start).total_seconds() // 60)
                                  if start and end else None),
                problem_count=_as_int(row.get("problemCount")) or 0,
                participant_count=_as_int(row.get("userCount")) or 0,
                is_rated=False, is_paid=bool(setting.get("needCharge")),
                rated_source=PROFILE_RATED_SOURCE,
                rated_comment="官方行级 ratingStatus=NO（不计分场次，仅展示）",
                raw_meta={"source": PROFILE_SOURCE})
        elif contest.is_rated:
            skipped += 1
            continue
        Participation.objects.create(
            contest=contest, platform_account=account,
            handle=account.handle, handle_lower=account.handle.lower(),
            display_name=str(row.get("teamName") or account.handle)[:150],
            raw_display_name=str(row.get("teamName") or "")[:200],
            rank=rank,
            solved_count=_as_int(row.get("acceptedCount")),
            total_score=row.get("totalScore") if isinstance(row.get("totalScore"),
                                                            (int, float)) else None,
            extra={"source": PROFILE_SOURCE,
                   "problem_count": _as_int(row.get("problemCount")),
                   "full_score": row.get("fullScore"),
                   "sign_up_count": _as_int(row.get("signUpCnt"))})
        created += 1
        log(f"  展示行落库 src={cid} rank={rank} {contest.name[:24]}")
    if created:
        logger.info("牛客主页不计分场次建行 account=%s 新增 %s 行", account.pk, created)
    return {"created": created, "skipped": skipped}


def refresh_nowcoder_history(account, *, scraper=None):
    """刷新单个牛客账号的参赛索引，并顺带做逐行交叉校验（B）。

    索引口径 = rating-history ∪ 个人主页已结束场次。后者是超集：2026-09-22 实测
    学生榜第一名 rating-history 25 场、主页 32 场，站内缺的 6 行全在差集里 ——
    只按 rating-history 建索引时这些缺口结构性不可见，换源才补得动。

    反爬约束：一个账号一次调用只打一次主页接口（scraper 内有进程级缓存），
    取数失败/返回空都**不写索引**，避免把「被静默置空」当成「该用户无历史」。
    """
    _crawler_dir()
    if scraper is None:
        from nowcoder_scraper import NowCoderScraper
        scraper = NowCoderScraper()
        scraper.init_session()

    hist = scraper.user_rating_history(account.handle)
    rh_ids, violations = rating_history_index_ids(hist)
    joined = scraper.contest_joined_history(account.handle)
    rows, complete, ok = [], False, bool(rh_ids)
    if joined is None:
        logger.warning("牛客主页参赛记录取数失败 account=%s，本轮索引只用 rating-history",
                       account.pk)
    else:
        rows = joined.get("rows") or []
        complete = bool(joined.get("complete"))
        ok = True
        if not rows and rh_ids:
            ok = False
            logger.warning("牛客主页参赛记录返回 0 行，但同账号 rating-history 有 %s 行"
                           "（account=%s）—— 按被拦处置，不当作无历史",
                           len(rh_ids), account.pk)
        elif not complete:
            logger.warning("牛客主页参赛记录未取全 account=%s（已取 %s 行），"
                           "本轮只按已取到的部分并索引", account.pk, len(rows))

    index_ids = rh_ids | joined_index_contest_ids(rows)
    mismatch = compare_nowcoder_history(account, rows)
    before = {str(x) for x in (account.participated_contests or [])}
    # 伪赛次（比赛违规）即使在旧索引里也要剔出去，否则变成一个永远补不出的假缺口
    target = (before | index_ids) - violations
    added = sorted(target - before, key=lambda s: int(s) if s.isdigit() else 0)
    removed = sorted(before - target, key=lambda s: int(s) if s.isdigit() else 0)
    updated = False
    if target != before:
        account.participated_contests = sorted(
            target, key=lambda s: int(s) if s.isdigit() else 0)
        account.save(update_fields=["participated_contests", "updated_at"])
        updated = True
        if added:
            logger.info("牛客参赛索引换源后新增 account=%s %s 场: %s",
                        account.pk, len(added), added[:10])
    if removed:
        logger.info("牛客参赛索引剔除伪赛次 account=%s: %s", account.pk, removed)
    materialized = materialize_profile_rows(account, rows)
    return {"ok": ok, "complete": complete, "rows": rows,
            "index_count": len(index_ids), "added": added, "removed": removed,
            "materialized": materialized,
            "mismatch": mismatch, "updated": updated}


def _meta_from_contest(contest):
    """用库里的 Contest 还原一份 ingest 需要的 meta（沿用 raw_meta 保原貌）。"""
    meta = dict(contest.raw_meta or {})
    meta.update({
        "real_contest_id": contest.external_id,
        "contest_id": contest.external_id,
        "name": contest.name,
        "link": contest.url,
        "is_rated": contest.is_rated,
        "is_paid": contest.is_paid,
        "duration_minutes": contest.duration_minutes,
        "series": contest.series,
        "rated_source": contest.rated_source,
        "rated_comment": contest.rated_comment,
    })
    if not meta.get("start_time") and contest.start_time:
        meta["start_time"] = contest.start_time.isoformat()
    if not meta.get("end_time") and contest.end_time:
        meta["end_time"] = contest.end_time.isoformat()
    return meta


def backfill_account_history(account, *, scraper=None, limit=0,
                             dry_run=False, log=None):
    """定向补齐一个牛客账号的历史参赛记录，结尾连带回填其 rating 涨落。

    存在的理由：每日全量爬取受「窗口月份 + 55 分钟软超时」约束，待补历史按
    时间降序排在最后，越老的越永远排不到（2026-09 Chen777iii、2026-09-22
    不知名小帅是同一失效模式的两次复现）。抓取顺序把「本地已有榜单原文」的
    场次排前面——那些一场只要几毫秒，而重新下载要 90~300 秒。
    """
    from apps.crawler.tasks import _contest_cache_ttl, _crawler_cache_dir

    log = log or (lambda msg: None)
    if account.platform != Platform.NOWCODER:
        raise ValueError("backfill_account_history 目前只支持牛客账号")

    _crawler_dir()
    from cache_util import cache_path
    # dry-run 只用「索引 vs 在库行 + 本地是否有原文」判断，一次外网请求都不该发
    if scraper is None and not dry_run:
        from nowcoder_scraper import NowCoderScraper
        scraper = NowCoderScraper()
        scraper.init_session()

    # 先把索引换成「rating-history ∪ 主页已结束场次」再算缺口：主页接口取数失败时
    # refresh 内部会退回 rating-history，不会把被拦当成无历史。dry-run 不发网络请求。
    verify = None
    hist_rows = []
    if not dry_run:
        res = refresh_nowcoder_history(account, scraper=scraper)
        verify = res["mismatch"]
        hist_rows = res["rows"]
        if res["added"]:
            log(f"索引新增 {len(res['added'])} 场: {res['added'][:8]}")

    missing = missing_nowcoder_contest_ids(account)
    if not missing:
        log(f"账号 {account.handle} 无待补场次")
        if not dry_run:
            backfill_nowcoder_ratings(account_ids=[account.pk])
        return {"pending": 0, "ingested": 0, "skipped": 0, "failed": 0,
                "verify": verify}

    cache_dir = _crawler_cache_dir(Platform.NOWCODER)
    in_db = {c.external_id: c for c in Contest.objects.filter(
        platform=Platform.NOWCODER, external_id__in=missing)}

    def _has_cache(eid):
        return bool(cache_dir) and cache_path(cache_dir, eid).exists()

    # 牛客 contestId 随时间单调递增，降序即「最新优先」；零网络场次排最前
    ordered = sorted(missing, key=lambda e: (0 if _has_cache(e) else 1,
                                             -int(e) if e.isdigit() else 0))
    if dry_run:
        for eid in ordered:
            log(f"  待补 src={eid} {'[本地缓存]' if _has_cache(eid) else '[需联网]'} "
                f"{in_db[eid].name if eid in in_db else '(比赛未入库)'}")
        return {"pending": len(ordered), "ingested": 0, "skipped": 0,
                "failed": 0, "dry_run": True}

    limit = limit or len(ordered)
    ingested = skipped = failed = 0
    for i, eid in enumerate(ordered[:limit], 1):
        try:
            contest = in_db.get(eid)
            if contest is not None:
                # 已入库 = rated/付费早已判过，直接复用，省一次 contest-info
                meta = _meta_from_contest(contest)
            else:
                info = scraper.fetch_contest_info(eid, use_cache=False)
                if not info:
                    failed += 1
                    log(f"[{i}/{len(ordered)}] {eid} 详情获取失败")
                    continue
                meta = scraper.check_rated({"real_contest_id": eid})
                start_ts, end_ts = info.get("startTime"), info.get("endTime")
                meta.update({
                    "real_contest_id": eid,
                    "contest_id": eid,
                    "name": info.get("name") or str(eid),
                    "start_time": scraper._ts2str(start_ts),
                    "end_time": scraper._ts2str(end_ts),
                    "duration_minutes": (int((end_ts - start_ts) / 60000)
                                         if start_ts and end_ts else None),
                    "link": f"https://www.nowcoder.com/acm/contest/{eid}",
                })
                if not meta.get("is_rated"):
                    skipped += 1
                    log(f"[{i}/{len(ordered)}] {eid} 非 rated 跳过"
                        f"（{meta.get('rated_comment')}）")
                    continue
            detail = scraper.scrape_contest_detail(
                eid, filter_post_contest=True, exclude_cheaters=False,
                cache_dir=cache_dir, cache_ttl_hours=_contest_cache_ttl(meta))
            result = ingest_contest(Platform.NOWCODER, meta, detail)
            if result.get("skipped"):
                skipped += 1
                log(f"[{i}/{len(ordered)}] {eid} 跳过: {result.get('reason')}")
                continue
            ingested += 1
            log(f"[{i}/{len(ordered)}] {eid} {meta.get('name', '')[:24]} "
                f"入库 计分 {result['countable']} 条")
        except Exception as exc:  # noqa: BLE001 - 单场失败不阻断其余场次
            failed += 1
            log(f"[{i}/{len(ordered)}] {eid} 异常: {exc}")
            logger.exception("牛客历史定向补抓失败 account=%s src=%s",
                             account.pk, eid)

    rating = backfill_nowcoder_ratings(account_ids=[account.pk])
    # 补完再对账一次：主页行还在 scraper 进程级缓存里，零额外请求，且这时
    # 「补上了没有」才是真答案 —— 用补数前的快照会把刚填的缺口报成缺行。
    if hist_rows:
        verify = compare_nowcoder_history(account, hist_rows)
    log(f"补齐完成: 入库 {ingested} / 跳过 {skipped} / 失败 {failed}，"
        f"rating 回填 {rating}")
    return {"pending": len(ordered), "ingested": ingested,
            "skipped": skipped, "failed": failed, "rating": rating,
            "verify": verify}


def fill_participated_contests(platform_account):
    """按官方个人历史接口补全单个 PlatformAccount 的参与比赛索引。

    Codeforces -> user.rating（contestId 列表）
    AtCoder    -> users/{handle}/history/json（ContestScreenName 列表）
    牛客       -> refresh_nowcoder_history：rating-history ∪ 个人主页已结束场次

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
        res = refresh_nowcoder_history(platform_account, scraper=scraper)
        return res["updated"], res["index_count"]
    else:
        return False, 0

    ids = [str(x) for x in ids if x not in (None, "")]
    merged = sorted(set(platform_account.participated_contests or []) | set(ids))
    if merged != list(platform_account.participated_contests or []):
        platform_account.participated_contests = merged
        platform_account.save(update_fields=["participated_contests", "updated_at"])
        return True, len(ids)
    return False, len(ids)

