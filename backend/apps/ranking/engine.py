"""
#5 积分排名引擎。

设计决策（已与用户确认）：
- 基础分 base_score = 100 * (1 - (rank-1) / max(1, valid_participant_count))
  名次归一化，参与即得分，第 1 名≈100、末位≈0；不依赖平台 rating，三平台通用。
- 综合系数 combined = platform_weight * 平台系数 + contest_weight * 比赛难度系数（加权求和）
- 最终积分 final = base * combined
- recent_contest_limit：仅个人榜取各平台最近 N 场求和；学校榜仍汇总成员全部有效场次。
- 周期 period：'all' + 当前年份；触发方式见 management 命令 / Celery 任务。
- 学校无专属 ScoreConfig 时回退全局默认（school=None 那条）。
"""
from collections import defaultdict
from datetime import datetime

from django.db.models import Count, Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.ranking.models import RankSnapshot, ScoreRecord
from apps.schools.models import ScoreConfig, School

# 生成的快照周期：全部 + 当前年份
ALL_PERIODS = ["all", str(timezone.now().year)]


def get_school_config(school):
    """取学校的积分配置，缺失时回退全局默认（school=None）。"""
    if school is not None:
        cfg = ScoreConfig.objects.filter(school=school).first()
        if cfg is not None:
            return cfg
    return ScoreConfig.objects.filter(school__isnull=True).first()


def compute_base_score(participation):
    """名次归一化基础分。rank 或有效人数缺失时记 0。"""
    rank = participation.rank
    contest = participation.contest
    vp = contest.valid_participant_count or contest.participant_count or 0
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

    # 清理已不再可计分的旧 ScoreRecord（如参赛被标记作弊/付费）
    deleted, _ = ScoreRecord.objects.exclude(
        participation_id__in=countable_ids).delete()

    created = updated = 0
    for p in countable:
        school = p.platform_account.school
        config = get_school_config(school)
        base = compute_base_score(p)
        pf, cf, combined = compute_factors(p, config)
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
                "contest_factor": cf,
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


def _build_school_rows(period):
    qs = _period_filter(ScoreRecord.objects.all(), period)
    agg = qs.values("school").annotate(
        total=Sum("final_score"),
        cnt=Count("id"),
        members=Count("platform_account__user", distinct=True),
    )
    rows = []
    for a in agg:
        if a["school"] is None:
            continue
        rows.append(RankSnapshot(
            scope=RankSnapshot.Scope.SCHOOL,
            period=period,
            school_id=a["school"],
            total_score=round(a["total"] or 0.0, 4),
            contest_count=a["cnt"] or 0,
            member_count=a["members"] or 0,
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
    school_ids = {u.school_id for u in users.values() if u.school_id}
    # 预取各用户当前学校的配置，取各平台最近 N 场
    schools = {s.id: s for s in School.objects.filter(id__in=school_ids)}

    rows = []
    for uid, recs in by_user.items():
        user = users.get(uid)
        config = get_school_config(user.school if user else None)
        limit = config.recent_contest_limit if config else 0
        if limit:
            by_plat = defaultdict(list)
            for r in recs:
                by_plat[r.platform].append(r)
            chosen = []
            for plist in by_plat.values():
                plist.sort(
                    key=lambda x: x.contest_time or datetime.min,
                    reverse=True)
                chosen.extend(plist[:limit])
            recs = chosen
        total = sum(r.final_score for r in recs)
        rows.append(RankSnapshot(
            scope=RankSnapshot.Scope.STUDENT,
            period=period,
            user_id=uid,
            total_score=round(total, 4),
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
