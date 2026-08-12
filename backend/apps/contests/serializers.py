"""参赛记录相关序列化器。"""
from rest_framework import serializers

from apps.contests.models import Contest, Participation


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

    class Meta:
        model = Participation
        fields = [
            "id", "contest", "contest_name", "contest_platform",
            "contest_platform_display", "contest_start_time", "contest_is_rated",
            "contest_url", "platform", "platform_account", "user_username",
            "handle", "display_name", "rank", "solved_count", "penalty_ms",
            "rating_delta", "old_rating", "new_rating", "is_excluded",
            "exclude_reason", "exclude_reason_display", "created_at",
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
    exclude_reason_display = serializers.CharField(
        source="get_exclude_reason_display", read_only=True)

    class Meta:
        model = Participation
        fields = [
            "id", "contest", "contest_name", "contest_platform",
            "contest_platform_display", "contest_start_time", "contest_is_rated",
            "platform_account", "user_username", "user_real_name",
            "handle", "display_name", "rank", "total_score", "solved_count",
            "is_excluded", "exclude_reason", "exclude_reason_display",
            "created_at",
        ]
        read_only_fields = fields
