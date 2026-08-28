"""赛季服务：当前赛季判定、阶段推进、进度计算、用户赛季战绩聚合。

设计要点：
- 赛季数据源是 Season 表（每年一条），SeasonConfig 只记录 current_season 指针。
- 阶段（stage）由时间自动推导并落库：
    * 未开始：now < start_at
    * 进行中：start_at <= now < end_at
    * 结算中：end_at <= now < settle_at（无 settle_at 则跳过）
    * 已结束：settle_at <= now（无 settle_at 则以 end_at 为准）
- 用户当前赛季战绩从 RankSnapshot 实时读（student/2026），不做额外冗余。
"""
from datetime import timedelta

from django.utils import timezone

from apps.ranking.models import RankSnapshot, Season, SeasonConfig


def _ensure_season(year):
    """按年份补齐一条赛季记录（默认起止 = 自然年）。不存在则创建。"""
    start = timezone.make_aware(
        __import__("datetime").datetime(year, 1, 1, 0, 0, 0))
    end = timezone.make_aware(
        __import__("datetime").datetime(year, 12, 31, 23, 59, 59))
    season, _ = Season.objects.get_or_create(
        year=year,
        defaults={"start_at": start, "end_at": end, "stage": Season.Stage.ACTIVE})
    return season


def derive_stage(season, now=None):
    """按时间推导赛季所处阶段。"""
    now = now or timezone.now()
    if now < season.start_at:
        return Season.Stage.UPCOMING
    if now < season.end_at:
        return Season.Stage.ACTIVE
    if season.settle_at and now < season.settle_at:
        return Season.Stage.SETTLING
    return Season.Stage.ENDED


def refresh_stages():
    """批量刷新所有赛季的阶段状态（定时任务或接口触发）。"""
    now = timezone.now()
    for s in Season.objects.all():
        stage = derive_stage(s, now)
        if s.stage != stage:
            s.stage = stage
            s.save(update_fields=["stage", "updated_at"])


def get_current_season():
    """返回当前赛季（含自动补建 + 阶段刷新 + 推进 current_season 指针）。"""
    now = timezone.now()
    year = now.year
    cfg = SeasonConfig.get_config()

    # 年度推进：current_season 落后于当前年份时自动推进（幂等）
    if cfg.current_season != year:
        cfg.current_season = year
        cfg.save(update_fields=["current_season", "updated_at"])

    season = _ensure_season(year)
    stage = derive_stage(season, now)
    if season.stage != stage:
        season.stage = stage
        season.save(update_fields=["stage", "updated_at"])
    return season


def season_progress(season, now=None):
    """赛季进度：已过天数 / 总天数（百分比）。"""
    now = now or timezone.now()
    total = (season.end_at - season.start_at).total_seconds()
    elapsed = (now - season.start_at).total_seconds()
    if total <= 0:
        return {"elapsed_days": 0, "total_days": 0, "pct": 0}
    elapsed = max(0, min(elapsed, total))
    pct = round(elapsed / total * 100, 1)
    return {
        "elapsed_days": int(elapsed // 86400),
        "total_days": int(total // 86400),
        "pct": pct,
    }


def settle_countdown(season, now=None):
    """结算倒计时（秒）。未配置 settle_at 或已过期返回 None。"""
    now = now or timezone.now()
    if not season.settle_at:
        return None
    delta = (season.settle_at - now).total_seconds()
    return max(0, int(delta))


def user_season_stats(user_id, season_year):
    """用户当前赛季战绩：从学生榜快照读排名 / 总积分 / 场次。"""
    snap = (RankSnapshot.objects
            .filter(scope=RankSnapshot.Scope.STUDENT,
                    period=str(season_year), user_id=user_id)
            .first())
    if snap is None:
        return {"rank": None, "total_score": 0, "contest_count": 0}
    return {
        "rank": snap.rank,
        "total_score": snap.total_score,
        "contest_count": snap.contest_count,
    }


def season_payload(season, user=None):
    """组装赛季信息 dict（前端 /season/ 接口直接使用）。"""
    now = timezone.now()
    progress = season_progress(season, now)
    countdown = settle_countdown(season, now)
    payload = {
        "id": season.id,
        "year": season.year,
        "name": season.name,
        "start_at": season.start_at.isoformat(),
        "end_at": season.end_at.isoformat(),
        "settle_at": season.settle_at.isoformat() if season.settle_at else None,
        "stage": season.stage,
        "stage_display": season.get_stage_display(),
        "rewards": season.rewards or [],
        "progress": progress,
        "settle_countdown_seconds": countdown,
    }
    if user is not None and user.is_authenticated:
        payload["me"] = user_season_stats(user.id, season.year)
    else:
        payload["me"] = None
    return payload


def past_seasons(limit=10):
    """往期赛季列表（按年份倒序，不含当前赛季）。"""
    now = timezone.now()
    qs = Season.objects.filter(year__lt=now.year).order_by("-year")[:limit]
    return [
        {
            "id": s.id,
            "year": s.year,
            "name": s.name,
            "start_at": s.start_at.isoformat(),
            "end_at": s.end_at.isoformat(),
            "stage": s.stage,
            "stage_display": s.get_stage_display(),
        }
        for s in qs
    ]
