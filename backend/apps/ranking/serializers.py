"""ranking 序列化器。"""
from rest_framework import serializers

from apps.ranking.models import RankSnapshot


class RankSnapshotSerializer(serializers.ModelSerializer):
    """只读展示榜单快照。"""

    school_name = serializers.CharField(source="school.name", read_only=True,
                                         allow_null=True)
    user_name = serializers.CharField(source="user.username", read_only=True,
                                       allow_null=True)
    user_school_name = serializers.CharField(source="user.school.name",
                                             read_only=True, allow_null=True)

    class Meta:
        model = RankSnapshot
        fields = [
            "id", "scope", "period", "school", "school_name", "user",
            "user_name", "user_school_name", "rank", "total_score",
            "contest_count", "member_count", "computed_at",
        ]
        read_only_fields = fields
