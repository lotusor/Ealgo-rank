"""
schools 视图：
- 列表 / 详情：公开可读（list 仅返回启用中的学校，支持 name/code 搜索）
- 增 / 改 / 删：仅超级管理员
- 管理员申请 / 审批：见 SchoolAdminApplicationViewSet
"""
from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    SAFE_METHODS,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from apps.accounts.models import (
    NotificationType,
    User as AccountUser,
    UserRole,
    notify,
)
from apps.common.permissions import IsSuperAdmin, IsSchoolAdmin
from apps.schools.models import (
    AdminApplicationStatus,
    School,
    SchoolAdminApplication,
    ScoreConfig,
)
from apps.schools.serializers import (
    SchoolAdminApplicationCreateSerializer,
    SchoolAdminApplicationReviewSerializer,
    SchoolAdminApplicationSerializer,
    ScoreConfigSerializer,
    SchoolSerializer,
)
from config.pagination import StandardPagination


class SchoolViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolSerializer
    queryset = School.objects.all()
    search_fields = ["name", "short_name", "code"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        qs = School.objects.annotate(member_count=Count("members"))
        if self.action == "list":
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        # 读开放，写仅超管（含危险操作）
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticatedOrReadOnly()]
        return [IsSuperAdmin()]


class SchoolAdminApplicationViewSet(viewsets.ModelViewSet):
    """
    学校管理员申请与审批流。

    可见范围：
      - 超级管理员：全部申请
      - 普通用户：仅自己提交的申请
    筛选：status（多选）、keyword（reason / contact 模糊）
    分页：StandardPagination（page + page_size，默认 20）
    审批动作（仅超管）：approve / reject / cancel（本人撤回待审）
    """

    serializer_class = SchoolAdminApplicationSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post"]  # 不允许 PUT/PATCH/DELETE，状态走动作

    def get_queryset(self):
        qs = SchoolAdminApplication.objects.select_related(
            "applicant", "school", "reviewer"
        ).all()
        user = self.request.user
        # 非超管只能看自己的
        if not (user and user.is_super_admin):
            qs = qs.filter(applicant=user)
        # 状态多选筛选
        statuses = self.request.query_params.getlist("status")
        if statuses:
            qs = qs.filter(status__in=statuses)
        # 关键词：reason 或 contact 模糊
        kw = self.request.query_params.get("keyword")
        if kw:
            qs = qs.filter(Q(reason__icontains=kw) | Q(contact__icontains=kw))
        return qs

    # ---------- 提交申请 ----------
    def get_serializer_class(self):
        if self.action == "create":
            return SchoolAdminApplicationCreateSerializer
        return SchoolAdminApplicationSerializer

    def perform_create(self, serializer):
        application = serializer.save(applicant=self.request.user)
        # 站内信通知所有超级管理员
        school_name = application.school.name
        for sa in AccountUser.objects.filter(role=UserRole.SUPER_ADMIN):
            notify(
                sa,
                "新的学校管理员申请",
                f"{application.applicant.username} 申请成为「{school_name}」的管理员",
                type=NotificationType.APPLICATION_RECEIVED,
                link=f"/admin/applications/{application.id}",
            )

    # ---------- 审批：通过 ----------
    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin])
    def approve(self, request, pk=None):
        application = self.get_object()
        if application.status != AdminApplicationStatus.PENDING:
            return Response(
                {"detail": "只有待审状态的申请可以审批"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        applicant = application.applicant
        school = application.school

        # 副作用：更新申请人角色 + 归属学校 + 同步名下平台账号
        applicant.role = UserRole.SCHOOL_ADMIN
        applicant.school = school
        from django.utils import timezone
        applicant.school_bound_at = timezone.now()
        applicant.save(update_fields=["role", "school", "school_bound_at"])
        synced = applicant.sync_platform_accounts_school()

        application.status = AdminApplicationStatus.APPROVED
        application.reviewer = request.user
        application.reviewed_at = timezone.now()
        application.save(update_fields=["status", "reviewer", "reviewed_at"])

        notify(
            applicant,
            "管理员申请已通过",
            f"你对「{school.name}」的管理员申请已通过，名下 {synced} 个平台账号已同步至该校",
            type=NotificationType.APPLICATION_REVIEWED,
            link=f"/admin/applications/{application.id}",
        )
        return Response(self.get_serializer(application).data)

    # ---------- 审批：驳回 ----------
    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin])
    def reject(self, request, pk=None):
        application = self.get_object()
        if application.status != AdminApplicationStatus.PENDING:
            return Response(
                {"detail": "只有待审状态的申请可以审批"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        review_serializer = SchoolAdminApplicationReviewSerializer(
            data=request.data)
        review_serializer.is_valid(raise_exception=True)
        comment = review_serializer.validated_data.get("review_comment", "")

        from django.utils import timezone
        application.status = AdminApplicationStatus.REJECTED
        application.review_comment = comment
        application.reviewer = request.user
        application.reviewed_at = timezone.now()
        application.save(update_fields=["status", "review_comment",
                                        "reviewer", "reviewed_at"])

        notify(
            application.applicant,
            "管理员申请未通过",
            f"你对「{application.school.name}」的管理员申请被驳回"
            + (f"：{comment}" if comment else ""),
            type=NotificationType.APPLICATION_REVIEWED,
            link=f"/admin/applications/{application.id}",
        )
        return Response(self.get_serializer(application).data)

    # ---------- 撤回（仅本人、仅待审） ----------
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        application = self.get_object()
        if application.applicant_id != request.user.id:
            return Response(
                {"detail": "只能撤回自己的申请"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if application.status != AdminApplicationStatus.PENDING:
            return Response(
                {"detail": "只有待审状态的申请可以撤回"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone
        application.status = AdminApplicationStatus.CANCELLED
        application.reviewed_at = timezone.now()
        application.save(update_fields=["status", "reviewed_at"])
        return Response(self.get_serializer(application).data)


class ScoreConfigViewSet(viewsets.ModelViewSet):
    """
    积分系数配置。每校一份（school 非空），外加一条 school=None 的全局默认。
    - 超管：可读/写全部（含全局默认）
    - 校管：仅可读/写本校配置，不能动全局默认
    """
    serializer_class = ScoreConfigSerializer
    permission_classes = [IsSchoolAdmin]
    queryset = ScoreConfig.objects.select_related("school").all()

    def get_queryset(self):
        qs = ScoreConfig.objects.select_related("school").all()
        user = self.request.user
        if not user.is_super_admin:
            qs = qs.filter(school_id=user.school_id)
        return qs

    def perform_create(self, serializer):
        # 校管创建时强制绑定本校；超管可自由指定 school（含留空=全局默认）
        if not self.request.user.is_super_admin:
            serializer.save(school=self.request.user.school)
        else:
            serializer.save()
