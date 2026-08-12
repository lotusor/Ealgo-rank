"""schools 序列化器。"""
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
    """学校积分系数配置（全局默认配置的 school 为 null）。"""

    class Meta:
        model = ScoreConfig
        fields = [
            "id", "school", "cf_factor", "atcoder_factor", "nowcoder_factor",
            "default_contest_factor", "platform_weight", "contest_weight",
            "recent_contest_limit", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SchoolAdminApplicationCreateSerializer(serializers.ModelSerializer):
    """
    提交申请用。
    仅允许绑定系统已存在的学校（proposed_school_name 不启用）；
    evidence 为可选证明材料。
    """

    school = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.filter(is_active=True),
        help_text="要申请管理的学校 ID（仅限已存在的学校）")
    evidence = serializers.FileField(required=False, allow_null=True,
                                     help_text="证明材料（可选）")

    class Meta:
        model = SchoolAdminApplication
        fields = ["id", "school", "reason", "contact", "evidence",
                  "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        school = attrs.get("school")
        if request and getattr(request, "user", None) and school:
            exists = SchoolAdminApplication.objects.filter(
                applicant=request.user,
                school=school,
                status=AdminApplicationStatus.PENDING,
            ).exists()
            if exists:
                raise serializers.ValidationError(
                    {"school": "你已经有一条该学校的待审申请，请勿重复提交"})
        return attrs


class SchoolAdminApplicationReviewSerializer(serializers.Serializer):
    """驳回时附带审批意见（可选）。"""

    review_comment = serializers.CharField(required=False, allow_blank=True,
                                           max_length=500)
