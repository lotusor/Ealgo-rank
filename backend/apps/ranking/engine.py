"""
#5 积分排名引擎（v3 统一表现分）。

设计决策（2026-09-07 与用户确认，仿 CF 种子机制的逆向）：
- **表现分 perf**（每场）：`perf = 平台系数 × (难度基线 D + 400 × Φ⁻¹(1−名次百分位))`。
  含义即「预期排到该名次的水平值」——名次百分位经正态逆函数（CF seed 同款）
  换算成水平差，参赛人数自动进入分母（同为前 1%，大场权重与小场相同）。
  **平台 rating 完全不参与计分**：新手号 rating 再低，打出高名次照样拿高分。
- **难度基线 D**：按「平台 × 系列」查 ContestDifficultyFactor.perf_base
  （超管覆盖位），否则用代码默认表 PERF_BASES（跨平台已归一到站点尺度，
  依据：CF 按分部门槛 / AtCoder 按官方 rated 对象 / 牛客按官方计分上限规则）。
- **站点 rating**：最近 N 场 perf 的衰减加权平均（N = recent_contest_limit，
  decay = rating_decay，2026-09-06 引入），并叠加**先验虚拟位**——
  先验 rating_prior 作为比全部真实场次更旧的一场，权重 decay^m，
  新号从先验出发快速收敛（1 场后先验占 ~46%，5 场后 <11%），同 CF 新号机制。
- 学校榜 = 成员站点 rating 之和；快照同分并列（跳位制）。
- 周期 period：'all' + 当前年份。
"""
from collections import defaultdict
from datetime import datetime
from statistics import NormalDist

from django.utils import timezone

from apps.accounts.models import User
from apps.contests.models import ContestDifficultyFactor
from apps.ranking.models import RankSnapshot, ScoreRecord, UserBestRecord
from apps.schools.models import ScoreConfig

# 生成的快照周期：全部 + 当前年份
ALL_PERIODS = ["all", str(timezone.now().year)]

# 表现分离散度：名次每偏离中位 1 个 σ 对应的水平差（CF 种子公式的斜率）
PERF_SPREAD = 400.0
# 表现分上下限：防小场次极端 z 值产生天文分
PERF_MIN, PERF_MAX = 200.0, 4000.0

# 「平台 × 系列」难度基线默认表（站点尺度，跨平台归一；超管可按行覆盖）。
# 依据（2026-09 联网调研）：
#   CF：分部门槛即 rated 对象（Div1 ≥1900 / Div2 <1900 / Div3 <1600 / Div4 <1400）
#   AtCoder：官方 rated 对象（ABC 0-1999 / ARC 1200-2799 / AGC 世界级）
#   牛客：官方计分上限（周赛 <1600 / 小白月赛 <1500-2000 / 练习赛 <2400 /
#         挑战赛全员计分；官方口径「周赛难度≈ABC」）
PERF_BASES = {
    ("codeforces", "Div. 1"): 2200,
    ("codeforces", "Div. 1 + Div. 2"): 1500,
    ("codeforces", "Div. 2"): 1450,
    ("codeforces", "Div. 3"): 1150,
    ("codeforces", "Div. 4"): 1000,
    ("codeforces", "Educational"): 1350,
    ("codeforces", "Global"): 1500,
    ("atcoder", "ABC"): 800,
    ("atcoder", "ARC"): 1550,
    ("atcoder", "AGC"): 2400,
    ("nowcoder", "牛客小白月赛"): 850,
    ("nowcoder", "牛客周赛"): 950,
    ("nowcoder", "牛客练习赛"): 1350,
    ("nowcoder", "牛客挑战赛"): 1700,
    ("nowcoder", "牛客寒假算法基础集训营"): 1750,
    ("nowcoder", "牛客暑期多校训练营"): 1750,
}
PLATFORM_DEFAULT_BASE = {
    "codeforces": 1400,
    "atcoder": 900,
    "nowcoder": 1000,
}

_NORM = NormalDist()


def get_config():
    """返回全局唯一的积分配置（超管统一设置，不分学校）。"""
    return ScoreConfig.get_config()


def contest_perf_base(contest):
    """难度基线 D：超管覆盖位（ContestDifficultyFactor.perf_base）→
    代码默认表（系列精确匹配 → 前缀匹配）→ 平台默认。"""
    from apps.common.models import Platform

    platform = contest.platform
    series = (contest.series or "").strip()
    if series:
        obj = ContestDifficultyFactor.objects.filter(
            platform=platform, series=series).first()
        if obj is not None and obj.perf_base is not None:
            return float(obj.perf_base)
        if (platform, series) in PERF_BASES:
            return float(PERF_BASES[(platform, series)])
        for (p, s), base in PERF_BASES.items():
            if p == platform and series.startswith(s):
                return float(base)
    return float(PLATFORM_DEFAULT_BASE.get(platform, 1200))


def rank_z(rank, valid_count):
    """名次 → 标准分 z（越大越强）。

    百分位取 (rank-0.5)/vp 的中位修正；rank/vp 缺失或单人场无信息量 → 0
    （表现分落在难度基线上）。
    """
    if not rank or rank <= 0 or not valid_count or valid_count <= 1:
        return 0.0
    p = (rank - 0.5) / valid_count
    p = min(max(p, 1e-6), 1 - 1e-6)
    return _NORM.inv_cdf(1 - p)


def compute_performance(participation, config):
    """单场表现分：perf = pf × (D + S·z)，clamp 到 [200, 4000]。

    返回 (perf, z, base, pf)。
    """
    contest = participation.contest
    vp = contest.participant_count or contest.valid_participant_count or 0
    z = rank_z(participation.rank, vp)
    base = contest_perf_base(contest)
    pf = float(config.platform_factor(contest.platform))
    perf = pf * (base + PERF_SPREAD * z)
    return min(max(perf, PERF_MIN), PERF_MAX), z, base, pf


def compute_base_score(participation):
    """兼容字段：返回该场的名次百分位 z（ScoreRecord.base_score 语义 v3）。"""
    contest = participation.contest
    vp = contest.participant_count or contest.valid_participant_count or 0
    return round(rank_z(participation.rank, vp), 4)


def _period_filter(qs, period):
    if not period or period == "all":
        return qs
    import re
    if re.fullmatch(r"\d{4}", period):
        return qs.filter(contest_time__year=int(period))
    if re.fullmatch(r"\d{4}-\d{2}", period):
        y, m = period.split("-")
        return qs.filter(contest_time__year=int(y), contest_time__month=int(m))
    return qs.none()


def recompute_score_records():
    """重算所有 countable 参赛记录的表现分 ScoreRecord（upsert）。"""
    from apps.contests.models import Participation

    countable = Participation.objects.countable().select_related(
        "contest", "platform_account__school")
    countable_ids = set(countable.values_list("id", flat=True))

    # 清理已不再可计分的旧 ScoreRecord（如参赛被标记作弊）
    deleted, _ = ScoreRecord.objects.exclude(
        participation_id__in=countable_ids).delete()

    config = ScoreConfig.get_config()
    created = updated = 0
    for p in countable:
        school = p.platform_account.school
        perf, z, base, pf = compute_performance(p, config)
        formula = (f"D={base:.0f} + 400*{z:+.2f} (pf={pf:.2f})")
        obj, was_created = ScoreRecord.objects.update_or_create(
            participation=p,
            defaults={
                "platform_account": p.platform_account,
                "school": school,
                "platform": p.contest.platform,
                "base_score": round(z, 4),
                "platform_factor": pf,
                "contest_factor": base,
                "final_score": round(perf, 4),
                "formula": formula,
                "contest_time": p.contest.start_time,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated, "deleted": deleted}


def _site_rating(perfs_newest_first, config):
    """站点 rating：最近 N 场 perf 衰减加权平均 + 先验虚拟位。

    perfs 按时间降序（最新在前）。先验作为「比全部在场场次更旧的一场」，
    权重 decay^m（m = 实际计入窗口的场数）：
      1 场后先验约占 46%，3 场约 24%，5 场约 10%，10 场约 4%。
    注意：Decimal(0) 为 falsy，取配置值时禁止 `or` 短路（会把合法的 0
    替换成默认值——曾致 decay=0/prior=0 的测试口径失效）。
    """
    n_raw = getattr(config, "recent_contest_limit", None)
    n = int(n_raw) if n_raw is not None else 0
    decay_raw = getattr(config, "rating_decay", None)
    decay = float(decay_raw) if decay_raw is not None else 1.0
    prior_raw = getattr(config, "rating_prior", None)
    prior = float(prior_raw) if prior_raw is not None else 1200.0
    if not perfs_newest_first:
        return prior
    window = perfs_newest_first if n <= 0 else perfs_newest_first[:n]
    m = len(window)
    if decay <= 0:
        return float(window[0])
    if decay >= 1.0:
        return (sum(window) + prior) / (m + 1)
    weights = [decay ** k for k in range(m)]
    prior_w = decay ** m
    num = sum(w * s for w, s in zip(weights, window)) + prior_w * prior
    den = sum(weights) + prior_w
    return num / den


def _user_scores(records, config):
    """把某用户的 ScoreRecord（跨平台混合）聚合成站点 rating 与窗口明细。

    返回 (rating, window_records)；window_records 为计入窗口的记录
    （时间降序），供重演 / 历史时间线复用。
    """
    n = int(getattr(config, "recent_contest_limit", 0) or 0)
    ordered = sorted(records,
                     key=lambda r: r.contest_time or datetime.min,
                     reverse=True)
    window = ordered if n <= 0 else ordered[:n]
    rating = _site_rating([r.final_score for r in window], config)
    return rating, window


def _build_school_rows(period):
    config = ScoreConfig.get_config()
    qs = _period_filter(
        ScoreRecord.objects.select_related("platform_account__user",
                                           "platform_account__school"),
        period)
    records = list(qs)

    # 先按用户聚合「站点 rating」（跨平台单一窗口），再按学校求和
    by_user = defaultdict(list)
    for r in records:
        by_user[r.platform_account.user_id].append(r)

    by_school = defaultdict(lambda: {"total": 0.0, "members": set(),
                                     "cnt": 0})
    for uid, recs in by_user.items():
        school_id = recs[0].school_id
        if school_id is None:
            continue
        rating, _ = _user_scores(recs, config)
        agg = by_school[school_id]
        agg["total"] += rating
        agg["members"].add(uid)
        # 参赛场次 = 该成员「实际计入积分」的场次数（全部 countable 记录），
        # 而非「窗口场次」。积分值按窗口口径（见 _user_scores），勿混用。
        agg["cnt"] += len(recs)

    rows = []
    for school_id, agg in by_school.items():
        rows.append(RankSnapshot(
            scope=RankSnapshot.Scope.SCHOOL,
            period=period,
            school_id=school_id,
            total_score=round(agg["total"], 4),
            contest_count=agg["cnt"],
            member_count=len(agg["members"]),
        ))
    return rows


def _build_student_rows(period):
    config = ScoreConfig.get_config()
    qs = _period_filter(
        ScoreRecord.objects.select_related(
            "platform_account__user", "platform_account__school"),
        period)
    records = list(qs)
    by_user = defaultdict(list)
    for r in records:
        uid = r.platform_account.user_id
        if uid:
            by_user[uid].append(r)

    user_ids = list(by_user.keys())
    users = {u.id: u for u in User.objects.filter(id__in=user_ids)}

    rows = []
    for uid, recs in by_user.items():
        _user = users.get(uid)
        rating, _window = _user_scores(recs, config)
        rows.append(RankSnapshot(
            scope=RankSnapshot.Scope.STUDENT,
            period=period,
            user_id=uid,
            total_score=round(rating, 4),
            # 参赛场次 = 实际计入积分的全部场次数（非窗口场次）
            contest_count=len(recs),
            member_count=1,
        ))
    return rows


def recompute_snapshots(scope, period):
    """重算某一 scope + period 的榜单快照（先删后建；同分同名次，跳位制）。"""
    RankSnapshot.objects.filter(scope=scope, period=period).delete()
    if scope == RankSnapshot.Scope.SCHOOL:
        rows = _build_school_rows(period)
    else:
        rows = _build_student_rows(period)
    rows.sort(key=lambda r: r.total_score, reverse=True)
    now = timezone.now()
    prev_score = None
    prev_rank = 0
    for i, r in enumerate(rows, 1):
        # 同分并列同名次，其后名次跳号（竞赛惯例 1,1,3）
        if prev_score is not None and r.total_score == prev_score:
            r.rank = prev_rank
        else:
            r.rank = i
            prev_rank = i
            prev_score = r.total_score
        r.computed_at = now
    RankSnapshot.objects.bulk_create(rows)
    return len(rows)


def recompute_all(periods=None):
    """完整重算：ScoreRecord + 各 scope/period 快照。"""
    result = recompute_score_records()
    periods = periods or ALL_PERIODS
    snapshots = {}
    for scope in [RankSnapshot.Scope.SCHOOL, RankSnapshot.Scope.STUDENT]:
        for period in periods:
            n = recompute_snapshots(scope, period)
            snapshots[f"{scope}:{period}"] = n
    result["snapshots"] = snapshots
    return result


def rating_history(user_id):
    """站点 rating 时间线：沿时间轴每场赛后重算窗口 rating（与榜单口径一致）。

    返回按时间升序的列表：
      [{contest_id, contest_name, contest_time, platform, perf, rating,
        rank, participant_count}]
    供「全部」折线图使用——单一事实源在后端，前端不再自行聚合。
    """
    config = ScoreConfig.get_config()
    recs = list(
        ScoreRecord.objects
        .filter(participation__is_excluded=False,
                participation__platform_account__user_id=user_id)
        .select_related("participation__contest")
        .order_by("contest_time"))
    out = []
    perfs = []  # 时间升序累计
    for r in recs:
        perfs.append(r.final_score)
        rating = _site_rating(list(reversed(perfs)), config)
        p = r.participation
        out.append({
            "contest_id": p.contest_id,
            "contest_name": p.contest.name,
            "contest_time": r.contest_time,
            "platform": r.platform,
            "perf": round(r.final_score, 1),
            "rating": round(rating, 1),
            "rank": p.rank,
            "participant_count": (p.contest.participant_count
                                  or p.contest.valid_participant_count or 0),
        })
    return out


def update_user_best_records():
    """维护用户历史最佳纪录（学生榜口径，基于比赛演变重演）。

    对全部 countable 积分记录按比赛时间重演：每个「赛后时点」上，各用户的
    站点 rating（跨平台窗口 + 先验，与榜单口径一致），对该时点的全体用户
    排序得到**当时名次**。因此：
    - best_rank = 全部赛后时点中的最小名次，配对达成时的站点 rating 与时间；
    - best_score = 全部赛后时点中的最高站点 rating，配对当时名次与时间。

    重演是确定性的（只依赖 ScoreRecord 全历史），幂等；在每次快照重算
    完成后调用（Celery 任务与管理命令两条路径均覆盖）。
    """
    config = ScoreConfig.get_config()
    recs = (ScoreRecord.objects
            .filter(participation__is_excluded=False,
                    participation__platform_account__user__isnull=False,
                    contest_time__isnull=False)
            .select_related("participation__platform_account__user")
            .only("final_score", "contest_time",
                  "participation__platform_account__user_id"))
    # uid -> {contest_time: final_score}（同场重复入库取后者）
    series = defaultdict(dict)
    for r in recs:
        uid = r.participation.platform_account.user_id
        series[uid][r.contest_time] = r.final_score
    if not series:
        UserBestRecord.objects.all().delete()
        return

    # 按时间分组事件：t -> [uid, score]
    events = defaultdict(list)
    for uid, by_time in series.items():
        for t, score in by_time.items():
            events[t].append((uid, score))

    # 沿时间轴推进：每时点重算受影响用户的窗口 rating，全体排序，更新最佳
    occurred = defaultdict(list)  # uid -> [final_score 时间升序]
    totals = {}                   # uid -> 站点 rating
    best = {}
    for t in sorted(events):
        affected = set()
        for uid, score in events[t]:
            occurred[uid].append(score)
            affected.add(uid)
        for uid in affected:
            totals[uid] = _site_rating(list(reversed(occurred[uid])), config)
        board = sorted(totals.items(), key=lambda x: -x[1])
        for rank, (uid, total) in enumerate(board, 1):
            b = best.get(uid)
            if b is None:
                best[uid] = {
                    "best_rank": rank, "best_rank_score": total,
                    "best_rank_at": t, "best_score": total,
                    "best_score_rank": rank, "best_score_at": t,
                }
                continue
            # 同名次取更高评分（系数调整重演时口径更优者优先）
            if rank < b["best_rank"] or (rank == b["best_rank"]
                                         and total > b["best_rank_score"]):
                b.update(best_rank=rank, best_rank_score=total, best_rank_at=t)
            if total > b["best_score"]:
                b.update(best_score=total, best_score_rank=rank, best_score_at=t)

    for uid, fields in best.items():
        UserBestRecord.objects.update_or_create(user_id=uid, defaults=fields)
    # 清理孤儿：积分记录已不存在（数据被清/账号解绑）的旧纪录
    UserBestRecord.objects.exclude(user_id__in=best.keys()).delete()
