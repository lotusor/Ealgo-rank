"""
ranking 视图：
- 榜单快照：公开可读（按 scope / period / school / user 筛选 + 分页）
- 重算动作：仅超级管理员（同步触发引擎；生产建议走 Celery 任务）
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.common.permissions import IsSuperAdmin
from apps.ranking.cache import (
    RANKING_CACHE_TTL,
    bump_ranking_version,
    get_ranking_version,
    ranking_cache_key,
    safe_cache_get,
    safe_cache_set,
)
from apps.ranking.engine import recompute_all
from apps.ranking.models import RankSnapshot
from apps.ranking.serializers import RankSnapshotSerializer
from config.pagination import StandardPagination


class RankSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RankSnapshotSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = RankSnapshot.objects.select_related("school", "user", "user__school").all()
        scope = self.request.query_params.get("scope", "school")
        period = self.request.query_params.get("period", "all")
        qs = qs.filter(scope=scope, period=period)
        school = self.request.query_params.get("school")
        if school:
            qs = qs.filter(school_id=school)
        user = self.request.query_params.get("user")
        if user:
            qs = qs.filter(user_id=user)
        return qs

    def list(self, request, *args, **kwargs):
        """榜单列表：缓存序列化后的分页结果。

        命中缓存直接返回；未命中则走原分页逻辑并回写缓存。
        重算后版本号自增，所有旧 key 自然失效（再叠 TTL 兜底）。
        """
        version = get_ranking_version()
        key = ranking_cache_key(version, request)
        cached = safe_cache_get(key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200 and isinstance(response.data, dict):
            safe_cache_set(key, response.data, RANKING_CACHE_TTL)
        return response

    @action(detail=False, methods=["post"],
            permission_classes=[IsSuperAdmin])
    def recompute(self, request):
        """同步重算积分与榜单快照（超管）。"""
        result = recompute_all()
        bump_ranking_version()
        return Response(result, status=status.HTTP_200_OK)
