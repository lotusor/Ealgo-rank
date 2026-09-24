"""
参赛记录视图：
- 列表（只读，支持 user / contest / platform / is_excluded / exclude_reason / school 过滤）
- exclude / restore 动作：人工剔除与恢复（仅改 is_excluded，原因由模型自动置 MANUAL / 清空）
权限：学校管理员 / 超级管理员；学校管理员仅能见本校记录。
"""
from django.db.models import Count, Max, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.common.models import ExcludeReason, Platform
from apps.common.permissions import IsSchoolAdmin, IsSuperAdmin
from apps.contests.models import Contest, ContestDifficultyFactor, Participation
from apps.contests.serializers import (
    ContestDifficultyFactorSerializer,
    ContestSerializer,
    MyParticipationSerializer,
    ParticipationSerializer,
)
from config.pagination import StandardPagination


class ContestViewSet(viewsets.ReadOnlyModelViewSet):
    """比赛只读列表 / 详情（用户端展示，匿名可读）。

    过滤维度：
      platform / is_rated / name / series        常规检索
      start_after / start_before / end_after / end_before   时间区间（日历按月取场次）
      status=ongoing|upcoming|finished           按当前时间派生的赛事状态（不落库）
      search=<关键字>                             名称与赛事系列模糊匹配
      ordering=start_time|end_time|…             白名单排序
      include_calendar=1 / include_profile_only=1 捞回默认隐藏的行（排期行 / 锚点行）

    ⚠️ 默认行为（不带任何参数）保持不变：返回全部比赛、按 `-start_time` 排序，
    以免影响既有「比赛列表」页与难度系数设置页。
    """

    serializer_class = ContestSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Contest.objects.all()
    ordering = ["-start_time"]
    # 显式白名单：OrderingFilter 未设 ordering_fields 时会放开序列化器全部字段
    ordering_fields = [
        "start_time", "end_time", "duration_minutes",
        "participant_count", "created_at",
    ]
    # 启用 ?search=（此前未设 search_fields，SearchFilter 是空操作）
    search_fields = ["name", "series"]

    def get_queryset(self):
        from apps.crawler.ingest import (CALENDAR_RATED_SOURCE,
                                         PROFILE_RATED_SOURCE)

        qs = Contest.objects.all()
        qp = self.request.query_params
        # 个人主页派生的「不计分锚点赛次」不是真实赛事目录成员：它们存在只是为了
        # 让参赛记录能展示校内赛/同步赛，出现在「比赛列表」里会误导用户。
        # 后台排障要看全量时带 ?include_profile_only=1。
        if qp.get("include_profile_only") not in ("1", "true"):
            qs = qs.exclude(rated_source=PROFILE_RATED_SOURCE)
        # 未开赛的官方排期同理：本页语义是「检索历史赛事」，且默认按 start_time
        # 倒序，几十天后的比赛会顶到第一屏。日历页自己带 ?include_calendar=1 取回。
        if qp.get("include_calendar") not in ("1", "true"):
            qs = qs.exclude(rated_source=CALENDAR_RATED_SOURCE)
        if qp.get("platform"):
            qs = qs.filter(platform=qp["platform"])
        if qp.get("is_rated") in ("true", "1"):
            qs = qs.filter(is_rated=True)
        elif qp.get("is_rated") in ("false", "0"):
            qs = qs.filter(is_rated=False)
        if qp.get("name"):
            qs = qs.filter(name__icontains=qp["name"])
        if qp.get("series"):
            qs = qs.filter(series=qp["series"])
        if qp.get("start_after"):
            qs = qs.filter(start_time__gte=qp["start_after"])
        if qp.get("start_before"):
            qs = qs.filter(start_time__lte=qp["start_before"])
        # 结束时间区间：日历按月/周取场次时用（跨月赛事按结束时间归属）
        if qp.get("end_after"):
            qs = qs.filter(end_time__gte=qp["end_after"])
        if qp.get("end_before"):
            qs = qs.filter(end_time__lte=qp["end_before"])

        # 赛事状态由时间派生，不新增数据库字段。
        # 注：end_time 为空的记录只在不带 status 时可见（三平台爬虫均会写入
        # end_time，为空属异常数据，不猜测其状态）。
        status_param = (qp.get("status") or "").strip().lower()
        if status_param:
            now = timezone.now()
            if status_param == "ongoing":
                qs = qs.filter(start_time__lte=now, end_time__gt=now)
            elif status_param == "upcoming":
                qs = qs.filter(start_time__gt=now)
            elif status_param == "finished":
                qs = qs.filter(end_time__lte=now)
        return qs

    @action(detail=False, methods=["get"],
            permission_classes=[IsAuthenticatedOrReadOnly])
    def meta(self, request):
        """日历与筛选条所需的元数据（公开只读，与列表一致）。

        计数一律按**全量**统计、不受当前筛选影响，供前端渲染筛选条徽标。
        统计口径 = 列表默认口径再放进展期行（只排掉个人主页锚点）：日历要展示
        「即将开始」，而那些场次在排期阶段只以日历行存在，按列表默认口径筛会让
        这一栏恒为 0。另外给出 `catalog`（已收录真实赛次数），页头可以据此区分
        「已收录」与「含排期」。`rated` 同取这一口径，因此含排期里的预计计分场次
        ——那是各源在预告期给出的计分判定，不等于站内已收录的榜单场。
        路径为 `/api/v1/contests/meta/`；DefaultRouter 的动态列表路由先于
        详情路由匹配，因此不会被 `<pk>` 吃掉。
        """
        from apps.crawler.ingest import (CALENDAR_RATED_SOURCE,
                                         PROFILE_RATED_SOURCE)

        now = timezone.now()
        base = Contest.objects.all()
        # 锚点赛次只服务参赛记录展示，从来不算赛程（且都是历史场），一律不计入
        base = base.exclude(rated_source=PROFILE_RATED_SOURCE)
        catalog = base.exclude(rated_source=CALENDAR_RATED_SOURCE)
        counts = base.aggregate(
            total=Count("id"),
            ongoing=Count("id", filter=Q(start_time__lte=now, end_time__gt=now)),
            upcoming=Count("id", filter=Q(start_time__gt=now)),
            finished=Count("id", filter=Q(end_time__lte=now)),
            rated=Count("id", filter=Q(is_rated=True)),
        )
        platforms = [
            {
                "key": p.value,
                "label": p.label,
                "count": base.filter(platform=p.value).count(),
            }
            for p in Platform
        ]
        series = list(
            base.exclude(series="")
            .values_list("series", flat=True)
            .distinct()
            .order_by("series")
        )
        return Response({
            **counts,
            "catalog": catalog.count(),
            "platforms": platforms,
            "series": series,
            # 「最近同步」要说的是**真榜单**多久没动过了。日历行每天 03:00 都会刷新
            # crawled_at，按全表取 Max 会让这个信号恒为「今天」，看不出爬取停摆。
            "latest_sync_at": catalog.aggregate(
                value=Max("crawled_at"))["value"],
            "schedule_synced_at": Contest.objects.filter(
                rated_source=CALENDAR_RATED_SOURCE).aggregate(
                value=Max("crawled_at"))["value"],
        })


class ParticipationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ParticipationSerializer
    permission_classes = [IsSchoolAdmin]
    pagination_class = StandardPagination
    queryset = Participation.objects.all()
    ordering = ["-contest__start_time", "rank"]

    def get_queryset(self):
        # 只看已绑定记录：未绑定路人/作弊路人不落库（2026-09-07 决策），
        # 此过滤对历史遗留行同样防御性生效
        qs = Participation.objects.select_related(
            "contest", "platform_account__user", "platform_account__school"
        ).filter(platform_account__isnull=False)
        user = self.request.user
        if not user.is_super_admin:
            qs = qs.filter(platform_account__school_id=user.school_id)

        qp = self.request.query_params
        if qp.get("user"):
            qs = qs.filter(
                platform_account__user__username__icontains=qp["user"])
        if qp.get("contest"):
            qs = qs.filter(contest_id=qp["contest"])
        if qp.get("platform"):
            qs = qs.filter(contest__platform=qp["platform"])
        if qp.get("is_excluded") in ("true", "false", "0", "1"):
            qs = qs.filter(is_excluded=qp["is_excluded"] in ("true", "1"))
        if qp.get("exclude_reason"):
            qs = qs.filter(exclude_reason=qp["exclude_reason"])
        return qs

    @action(detail=True, methods=["post"],
            permission_classes=[IsSchoolAdmin])
    def exclude(self, request, pk=None):
        p = self.get_object()
        p.is_excluded = True
        p.exclude_reason = ExcludeReason.MANUAL
        p.save()
        return Response(ParticipationSerializer(p).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"],
            permission_classes=[IsSchoolAdmin])
    def restore(self, request, pk=None):
        p = self.get_object()
        p.is_excluded = False  # 模型 save() 会自动清空 exclude_reason
        p.save()
        return Response(ParticipationSerializer(p).data, status=status.HTTP_200_OK)


class MyParticipationViewSet(viewsets.ReadOnlyModelViewSet):
    """当前登录用户本人的参赛记录（只读，仅本人可见）。

    用于用户端「个人成绩」页：列出本人各平台参赛历史，并暴露 rating 涨跌相关
    字段，供前端标注名次变化与绘制积分变化折线图。与管理端 participations 不同，
    本接口不做学校隔离（天然只返回本人数据）。
    """

    serializer_class = MyParticipationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    ordering = ["-contest__start_time", "rank"]

    def get_queryset(self):
        qs = Participation.objects.filter(
            platform_account__user=self.request.user
        ).select_related("contest", "platform_account__user")
        qp = self.request.query_params
        if qp.get("platform"):
            qs = qs.filter(contest__platform=qp["platform"])
        if qp.get("is_excluded") in ("true", "false", "0", "1"):
            qs = qs.filter(is_excluded=qp["is_excluded"] in ("true", "1"))
        return qs


class ContestDifficultyFactorViewSet(viewsets.ModelViewSet):
    """比赛难度系数（平台 × 系列 → 系数），仅超管读写。"""

    serializer_class = ContestDifficultyFactorSerializer
    pagination_class = StandardPagination
    permission_classes = [IsSuperAdmin]
    queryset = ContestDifficultyFactor.objects.all()
    ordering = ["platform", "series"]

    def get_queryset(self):
        qs = ContestDifficultyFactor.objects.all()
        qp = self.request.query_params
        if qp.get("platform"):
            qs = qs.filter(platform=qp["platform"])
        return qs
