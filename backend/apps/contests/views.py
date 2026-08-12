"""
参赛记录视图：
- 列表（只读，支持 user / contest / platform / is_excluded / exclude_reason / school 过滤）
- exclude / restore 动作：人工剔除与恢复（仅改 is_excluded，原因由模型自动置 MANUAL / 清空）
权限：学校管理员 / 超级管理员；学校管理员仅能见本校记录。
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.common.models import ExcludeReason
from apps.common.permissions import IsSchoolAdmin
from apps.contests.models import Contest, Participation
from apps.contests.serializers import (
    ContestSerializer,
    MyParticipationSerializer,
    ParticipationSerializer,
)
from config.pagination import StandardPagination


class ContestViewSet(viewsets.ReadOnlyModelViewSet):
    """比赛只读列表 / 详情（用户端展示）。支持平台 / rated / 名称 / 时间过滤。"""
    serializer_class = ContestSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Contest.objects.all()
    ordering = ["-start_time"]

    def get_queryset(self):
        qs = Contest.objects.all()
        qp = self.request.query_params
        if qp.get("platform"):
            qs = qs.filter(platform=qp["platform"])
        if qp.get("is_rated") in ("true", "1"):
            qs = qs.filter(is_rated=True)
        elif qp.get("is_rated") in ("false", "0"):
            qs = qs.filter(is_rated=False)
        if qp.get("name"):
            qs = qs.filter(name__icontains=qp["name"])
        if qp.get("start_after"):
            qs = qs.filter(start_time__gte=qp["start_after"])
        if qp.get("start_before"):
            qs = qs.filter(start_time__lte=qp["start_before"])
        return qs


class ParticipationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ParticipationSerializer
    permission_classes = [IsSchoolAdmin]
    pagination_class = StandardPagination
    queryset = Participation.objects.all()
    ordering = ["-contest__start_time", "rank"]

    def get_queryset(self):
        qs = Participation.objects.select_related(
            "contest", "platform_account__user", "platform_account__school"
        ).all()
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
