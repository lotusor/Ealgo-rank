"""schools 序列化器。"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import User as AccountUser
from apps.schools.models import (
    AdminApplicationStatus,
    School,
    SchoolAdminApplication,
    ScoreConfig,
)


class SchoolSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True,
                                            help_text="成员数（注解字段）")

    class Meta:
        model = School
        fields = ["id", "name", "short_name", "code", "logo", "description",
                  "is_active", "member_count"]
        read_only_fields = ["id", "member_count"]


class _ApplicantMiniSerializer(serializers.ModelSerializer):
    """申请人简况（只读嵌套）。"""

    class Meta:
        model = AccountUser
        fields = ["id", "username", "real_name", "role"]
        read_only_fields = fields


class _SchoolMiniSerializer(serializers.ModelSerializer):
    """学校简况（只读嵌套）。"""

    class Meta:
        model = School
        fields = ["id", "name", "code"]
        read_only_fields = fields


class SchoolAdminApplicationSerializer(serializers.ModelSerializer):
    """只读展示用：嵌套申请人、学校、审批人。"""

    applicant = _ApplicantMiniSerializer(read_only=True)
    school = _SchoolMiniSerializer(read_only=True)
    reviewer = _ApplicantMiniSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display",
                                          read_only=True)

    class Meta:
        model = SchoolAdminApplication
        fields = [
            "id", "applicant", "school", "reason", "contact", "evidence",
            "status", "status_display", "review_comment", "reviewer",
            "reviewed_at", "created_at", "updated_at",
        ]
        read_only_fields = fields


class ScoreConfigSerializer(serializers.ModelSerializer):
    """全局唯一的积分系数配置。"""

    class Meta:
        model = ScoreConfig
        fields = [
            "id", "cf_factor", "atcoder_factor", "nowcoder_factor",
            "default_contest_factor", "platform_weight", "contest_weight",
            "recent_contest_limit", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        # 各系数非负
        for field in (
            "cf_factor", "atcoder_factor", "nowcoder_factor",
            "default_contest_factor", "platform_weight", "contest_weight",
        ):
            val = attrs.get(field)
            if val is not None and val < 0:
                raise serializers.ValidationError({field: "系数不能为负"})
        # 平台权重 + 比赛权重之和必须为 1
        pw = attrs.get("platform_weight")
        cw = attrs.get("contest_weight")
        if pw is not None and cw is not None and (pw + cw) != Decimal("1"):
            raise serializers.ValidationError(
                {"platform_weight": "平台权重与比赛权重之和必须等于 1"})
        rcl = attrs.get("recent_contest_limit")
        if rcl is not None and rcl < 0:
            raise serializers.ValidationError(
                {"recent_contest_limit": "计分场次上限不能为负"})
        return attrs


class SchoolAdminApplicationCreateSerializer(serializers.ModelSerializer):
    """
    提交申请用。两种模式二选一：
      - 绑定系统已存在的学校（school）
      - 申请系统里还没有的学校（proposed_school_name，审批通过时自动建档）
    """

    school = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.filter(is_active=True), required=False,
        allow_null=True,
        help_text="要申请管理的学校 ID（仅限已存在的学校）")
    proposed_school_name = serializers.CharField(
        required=False, allow_blank=True, max_length=100,
        help_text="申请系统里还没有的学校时填写，审批通过会自动建档")
    evidence = serializers.FileField(required=False, allow_null=True,
                                     help_text="证明材料（可选）")

    class Meta:
        model = SchoolAdminApplication
        fields = ["id", "school", "proposed_school_name", "reason", "contact",
                  "evidence", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        school = attrs.get("school")
        proposed = (attrs.get("proposed_school_name") or "").strip()

        # 已是管理员（校管/超管）禁止再次申请
        if user and (user.is_school_admin or user.is_super_admin):
            raise serializers.ValidationError(
                {"school": "你已是管理员，无需再次申请"})

        # 二选一：要么绑定已有学校，要么提出新建学校
        if not school and not proposed:
            raise serializers.ValidationError(
                {"school": "请选择已存在的学校，或填写要申请新建的学校名称"})

        if school:
            # 绑定已有学校时忽略 proposed_school_name
            attrs["proposed_school_name"] = ""
        else:
            # 系统里已有同名学校则引导直接申请该校
            if School.objects.filter(name=proposed, is_active=True).exists():
                raise serializers.ValidationError(
                    {"proposed_school_name":
                     "该系统已存在同名学校，请直接申请该校"})
            # 同一申请人对同一新建校名的待审申请去重（约束无法覆盖 NULL school）
            if user and SchoolAdminApplication.objects.filter(
                applicant=user, proposed_school_name=proposed,
                status=AdminApplicationStatus.PENDING,
            ).exists():
                raise serializers.ValidationError(
                    {"proposed_school_name":
                     "你已有一条该新建学校的待审申请，请勿重复提交"})

        # 每月仅限申请一次（跨学校也受此约束）
        if user:
            now = timezone.now()
            if SchoolAdminApplication.objects.filter(
                applicant=user,
                created_at__year=now.year,
                created_at__month=now.month,
            ).exists():
                raise serializers.ValidationError(
                    {"school": "你本月已提交过申请，请下月再试"})

        # 绑定已有学校时的待审去重
        if user and school:
            if SchoolAdminApplication.objects.filter(
                applicant=user,
                school=school,
                status=AdminApplicationStatus.PENDING,
            ).exists():
                raise serializers.ValidationError(
                    {"school": "你已经有一条该学校的待审申请，请勿重复提交"})
        return attrs


class SchoolAdminApplicationReviewSerializer(serializers.Serializer):
    """驳回时附带审批意见（可选）。"""

    review_comment = serializers.CharField(required=False, allow_blank=True,
                                           max_length=500)
