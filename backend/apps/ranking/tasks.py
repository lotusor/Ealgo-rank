"""积分引擎的 Celery 任务包装。

实际重算逻辑在 apps.ranking.engine；beat 调度规则归 #6 配置。
worker 未起时，管理命令 `recompute_ranking` 可直接同步跑。
"""
from celery import shared_task

from apps.ranking.cache import bump_ranking_version
from apps.ranking.engine import ALL_PERIODS, recompute_all, recompute_snapshots
from apps.ranking.models import RankSnapshot


@shared_task
def recompute_ranking_task(scope="all", period=None):
    """全量或指定 scope/period 重算。"""
    if period:
        scopes = ([scope] if scope != "all"
                  else [RankSnapshot.Scope.SCHOOL, RankSnapshot.Scope.STUDENT])
        total = 0
        for sc in scopes:
            total += recompute_snapshots(sc, period)
        result = {"period": period, "rows": total}
    else:
        result = recompute_all(periods=ALL_PERIODS)
    # 重算完成即让旧列表缓存失效
    bump_ranking_version()
    return result
