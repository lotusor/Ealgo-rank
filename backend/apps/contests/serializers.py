"""参赛记录相关序列化器。"""
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.contests.models import Contest, ContestDifficultyFactor, Participation


class ContestSerializer(serializers.ModelSerializer):
    """比赛只读展示（用户端列表/详情复用）。"""
    platform_display = serializers.CharField(
        source="get_platform_display", read_only=True)

    class Meta:
        model = Contest
        fields = [
            "id", "platform", "platform_display", "external_id", "name", "url",
            "start_time", "end_time", "duration_minutes", "is_rated", "is_paid",
            "series", "difficulty_factor", "problem_count", "participant_count",
            "valid_participant_count", "cheater_count", "created_at",
        ]
        read_only_fields = fields


class MyParticipationSerializer(serializers.ModelSerializer):
    """当前登录用户本人参赛记录（只读，仅本人可见）。

    相比管理端 ParticipationSerializer 额外暴露 rating_delta / old_rating /
    new_rating / penalty_ms，用于个人成绩页的涨跌标注与积分变化折线图。
    """

    contest_name = serializers.CharField(source="contest.name", read_only=True)
    contest_platform = serializers.CharField(
        source="contest.platform", read_only=True)
    contest_platform_display = serializers.CharField(
        source="contest.get_platform_display", read_only=True)
    contest_start_time = serializers.DateTimeField(
        source="contest.start_time", read_only=True)
    contest_is_rated = serializers.BooleanField(
        source="contest.is_rated", read_only=True)
    contest_url = serializers.URLField(source="contest.url", read_only=True)
    platform = serializers.CharField(
        source="platform_account.platform", read_only=True)
    user_username = serializers.CharField(
        source="platform_account.user.username", read_only=True, default="")
    exclude_reason_display = serializers.CharField(
        source="get_exclude_reason_display", read_only=True)
    # 「这一场为什么没有平台 rating」的现成文案（打星 / 超上限 / 空=正常）
    rating_note = serializers.CharField(read_only=True)

    class Meta:
        model = Participation
        fields = [
            "id", "contest", "contest_name", "contest_platform",
            "contest_platform_display", "contest_start_time", "contest_is_rated",
            "contest_url", "platform", "platform_account", "user_username",
            "handle", "display_name", "rank", "solved_count", "penalty_ms",
            "rating_delta", "old_rating", "new_rating",
            "is_excluded", "exclude_reason", "exclude_reason_display",
            "rating_note",
            "created_at",
        ]
        read_only_fields = fields


class ParticipationSerializer(serializers.ModelSerializer):
    contest_name = serializers.CharField(source="contest.name", read_only=True)
    contest_platform = serializers.CharField(
        source="contest.platform", read_only=True)
    contest_platform_display = serializers.CharField(
        source="contest.get_platform_display", read_only=True)
    contest_start_time = serializers.DateTimeField(
        source="contest.start_time", read_only=True)
    contest_is_rated = serializers.BooleanField(
        source="contest.is_rated", read_only=True)
    user_username = serializers.CharField(
        source="platform_account.user.username", read_only=True, default="")
    user_real_name = serializers.CharField(
        source="platform_account.user.real_name", read_only=True, default="")
    # 归属用户角色：管理动作「只能向下」，前端据此隐藏必然 403 的排除/恢复按钮
    user_role = serializers.CharField(
        source="platform_account.user.role", read_only=True, default="")
    exclude_reason_display = serializers.CharField(
        source="get_exclude_reason_display", read_only=True)
    rating_note = serializers.CharField(read_only=True)
    # 后台「积分」列的真值：积分引擎给出的单场表现分。
    # 之前这一格取的是 `total_score`（平台原始总分）—— 小白月赛/多校是 ICPC 制，
    # 官方 totalScore 恒为 0，于是「积分」列显示 0.0，看着像这人积分没了
    # （2026-10-12 kkl1 报障即此）。未计入积分的行没有 ScoreRecord → null，
    # 前端显示「—」而不是 0：0 和「没数据」是两回事。
    perf = serializers.SerializerMethodField()

    class Meta:
        model = Participation
        fields = [
            "id", "contest", "contest_name", "contest_platform",
            "contest_platform_display", "contest_start_time", "contest_is_rated",
            "platform_account", "user_username", "user_real_name", "user_role",
            "handle", "display_name", "rank", "total_score", "solved_count",
            "is_excluded", "exclude_reason", "exclude_reason_display",
            "rating_note", "perf", "extra", "created_at",
        ]
        read_only_fields = fields

    def get_perf(self, obj):
        try:
            return obj.score_record.final_score
        except ObjectDoesNotExist:
            return None


class ContestDifficultyFactorSerializer(serializers.ModelSerializer):
    """比赛难度配置（平台 × 系列 → 难度基线 D），超管读写。

    v3：perf_base 为表现分难度基线（rating 尺度）；factor 为旧口径乘数，
    保留展示与回滚参考，不参与计分。
    """

    platform_display = serializers.CharField(source="get_platform_display",
                                             read_only=True)

    class Meta:
        model = ContestDifficultyFactor
        fields = ["id", "platform", "platform_display", "series", "factor",
                  "perf_base", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate_factor(self, value):
        if value <= 0:
            raise serializers.ValidationError("难度系数必须大于 0")
        return value

    def validate_perf_base(self, value):
        if value is None:
            return value  # 空 = 用代码默认表
        if not (200 <= value <= 4000):
            raise serializers.ValidationError(
                "难度基线 D 应在 200~4000（rating 尺度）")
        return value
