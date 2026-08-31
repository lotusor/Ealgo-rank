"""
#5 积分排名引擎。

设计决策（已与用户确认 2026-08-24）：
- 积分排行采用「平台归一后的总 rating」= 各平台当前 rating × 平台系数 之和。
  - 每个平台取该用户「最新一场」的赛后 rating（new_rating），乘以平台系数，
    跨平台求和得到个人总 rating；学校榜 = 成员总 rating 之和。
  - rating 是「当前水平」而非「累加值」，故每个平台只取最新一场，不逐场累加。
- 名次归一化 base_score 保留为兜底：new_rating 缺失时才退回
  base = 100 * (1 - (rank-1)/valid_count)。
- 周期 period：'all' + 当前年份；触发方式见 management 命令 / Celery 任务。
- 积分系数为全局统一配置（超管设置），不分学校。
"""
from collections import defaultdict
from datetime import datetime

from django.db.models import Count, Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.contests.models import ContestDifficultyFactor
from apps.ranking.models import RankSnapshot, ScoreRecord, UserBestRecord
from apps.schools.models import ScoreConfig, School

# 生成的快照周期：全部 + 当前年份
ALL_PERIODS = ["all", str(timezone.now().year)]


def get_config():
    """返回全局唯一的积分配置（超管统一设置，不分学校）。"""
    return ScoreConfig.get_config()


def compute_base_score(participation):
    """名次归一化基础分（兜底用）。rank 或有效人数缺失时记 0。

    分母必须是「全场有效参赛人数」（participant_count），而不是
    valid_participant_count —— 后者在 ingest 里被写成本站已绑定人数
    （生产环境仅 1），若拿它当分母，名次稍靠后就会算出 -100 万量级的
    天文负分。rating 缺失时才走这条兜底，虽当前数据都有 rating，
    但字段一旦缺值即爆雷，必须修正。
    """
    rank = participation.rank
    contest = participation.contest
    vp = contest.participant_count or contest.valid_participant_count or 0
    if not rank or rank <= 0 or vp <= 0:
        return 0.0
    return round(100.0 * (1 - (rank - 1) / vp), 4)


def contest_factor_for(contest, config):
    """比赛难度系数：比赛显式设置（非默认 1.0）优先，否则回退学校默认。"""
    df = contest.difficulty_factor
    if df is None or float(df) == 1.0:
        return float(config.default_contest_factor)
    return float(df)


def compute_factors(participation, config):
    pf = float(config.platform_factor(participation.contest.platform))
    cf = contest_factor_for(participation.contest, config)
    combined = float(config.platform_weight) * pf + float(config.contest_weight) * cf
    return pf, cf, combined


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
    """重算所有 countable 参赛记录对应的 ScoreRecord（upsert）。"""
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
        base = compute_base_score(p)
        pf, cf, combined = compute_factors(p, config)
        # 比赛难度系数：按「平台 × 比赛系列」映射的独立乘区，命中不到回退 1.0
        difficulty = ContestDifficultyFactor.factor_for(
            p.contest.platform, p.contest.series)
        # rating 加权值 = rating × 平台系数 × 比赛难度系数；rating 缺失退回名次归一化
        if p.new_rating is not None:
            final = round(float(p.new_rating) * pf * difficulty, 4)
            formula = (f"rating={p.new_rating:.0f} * 平台系数{pf:.2f}"
                       f" * 难度系数{difficulty:.2f}")
        else:
            final = round(base * combined, 4)
            formula = (
                f"base={base:.2f} * "
                f"({float(config.platform_weight):.2f}*{pf:.2f}"
                f"+{float(config.contest_weight):.2f}*{cf:.2f})"
            )
        obj, was_created = ScoreRecord.objects.update_or_create(
            participation=p,
            defaults={
                "platform_account": p.platform_account,
                "school": school,
                "platform": p.contest.platform,
                "base_score": base,
                "platform_factor": pf,
                "contest_factor": difficulty,
                "final_score": final,
                "formula": formula,
                "contest_time": p.contest.start_time,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated, "deleted": deleted}


def _latest_by_platform(records):
    """把某用户的所有 ScoreRecord 按平台分组，取各平台最新一场。"""
    by_plat = defaultdict(list)
    for r in records:
        by_plat[r.platform].append(r)
    latest = []
    for plist in by_plat.values():
        plist.sort(key=lambda x: x.contest_time or datetime.min, reverse=True)
        latest.append(plist[0])
    return latest


def _build_school_rows(period):
    qs = _period_filter(
        ScoreRecord.objects.select_related("platform_account__user",
                                           "platform_account__school"),
        period)
    records = list(qs)

    # 先按用户聚合「各平台最新 rating 加权值之和」（个人总 rating），再按学校求和
    by_user = defaultdict(list)
    for r in records:
        by_user[r.platform_account.user_id].append(r)

    by_school = defaultdict(lambda: {"total": 0.0, "members": set(),
                                     "cnt": 0})
    for uid, recs in by_user.items():
        school_id = recs[0].school_id
        if school_id is None:
            continue
        latest = _latest_by_platform(recs)
        user_total = sum(r.final_score for r in latest)
        agg = by_school[school_id]
        agg["total"] += user_total
        agg["members"].add(uid)
        # 参赛场次 = 该成员「实际计入积分」的场次数（全部 countable 记录），
        # 而非「每平台最新一场数」。积分值仍只取每平台最新一场（见 _latest_by_platform），
        # 二者语义不同，勿混用。
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
        user = users.get(uid)
        latest = _latest_by_platform(recs)
        total = sum(r.final_score for r in latest)
        rows.append(RankSnapshot(
            scope=RankSnapshot.Scope.STUDENT,
            period=period,
            user_id=uid,
            total_score=round(total, 4),
            # 参赛场次 = 该用户实际计入积分的场次数（全部 countable 记录），
            # 而非每平台最新一场数（积分值仍只取每平台最新一场）
            contest_count=len(recs),
            member_count=1,
        ))
    return rows


def recompute_snapshots(scope, period):
    """重算某一 scope + period 的榜单快照（先删后建）。"""
    RankSnapshot.objects.filter(scope=scope, period=period).delete()
    if scope == RankSnapshot.Scope.SCHOOL:
        rows = _build_school_rows(period)
    else:
        rows = _build_student_rows(period)
    rows.sort(key=lambda r: r.total_score, reverse=True)
    now = timezone.now()
    for i, r in enumerate(rows, 1):
        r.rank = i
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


def update_user_best_records():
    """维护用户历史最佳纪录（学生榜口径，基于比赛演变重演）。

    对全部 countable 积分记录按比赛时间重演：每个「赛后时点」上，各用户取
    每平台最新一场 final_score 求和（与榜单口径一致），对该时点的全体用户
    排序得到**当时名次**。因此：
    - best_rank = 全部赛后时点中的最小名次，配对达成时的总 rating 与达成时间；
    - best_score = 全部赛后时点中的最高总 rating，配对当时名次与时间。

    重演是确定性的（只依赖 ScoreRecord 全历史），每次重算直接覆盖写入，
    并清理已无积分记录用户的孤儿纪录。幂等；在每次快照重算完成后调用
    （Celery 任务与管理命令两条路径均覆盖）。
    """
    recs = (ScoreRecord.objects
            .filter(participation__is_excluded=False,
                    participation__platform_account__user__isnull=False,
                    contest_time__isnull=False)
            .select_related("participation__platform_account__user")
            .only("platform", "final_score", "contest_time",
                  "participation__platform_account__user_id"))
    # (user_id, platform) -> {contest_time: final_score}（同场重复入库取后者）
    series = defaultdict(dict)
    for r in recs:
        uid = r.participation.platform_account.user_id
        series[(uid, r.platform)][r.contest_time] = r.final_score
    if not series:
        UserBestRecord.objects.all().delete()
        return

    # 按时间分组事件：t -> [(uid, platform, score)]
    events = defaultdict(list)
    for (uid, platform), by_time in series.items():
        for t, score in by_time.items():
            events[t].append((uid, platform, score))

    # 沿时间轴推进，每个赛后时点对全体用户求和排序，更新各用户最佳
    totals = defaultdict(dict)  # uid -> platform -> score
    best = {}  # uid -> dict(UserBestRecord 字段)
    for t in sorted(events):
        for uid, platform, score in events[t]:
            totals[uid][platform] = score
        board = sorted(
            ((uid, sum(pv.values())) for uid, pv in totals.items()),
            key=lambda x: -x[1])
        for rank, (uid, total) in enumerate(board, 1):
            b = best.get(uid)
            if b is None:
                best[uid] = {
                    "best_rank": rank, "best_rank_score": total,
                    "best_rank_at": t, "best_score": total,
                    "best_score_rank": rank, "best_score_at": t,
                }
                continue
            # 同名次取更高 rating（系数调整重演时口径更优者优先）
            if rank < b["best_rank"] or (rank == b["best_rank"]
                                         and total > b["best_rank_score"]):
                b.update(best_rank=rank, best_rank_score=total, best_rank_at=t)
            if total > b["best_score"]:
                b.update(best_score=total, best_score_rank=rank, best_score_at=t)

    for uid, fields in best.items():
        UserBestRecord.objects.update_or_create(user_id=uid, defaults=fields)
    # 清理孤儿：积分记录已不存在（数据被清/账号解绑）的旧纪录
    UserBestRecord.objects.exclude(user_id__in=best.keys()).delete()
