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
    # 用户头像：有则输出完整 URL（供榜单/跳转页展示），无则 null（前端回退首字母）
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = RankSnapshot
        fields = [
            "id", "scope", "period", "school", "school_name", "user",
            "user_name", "user_school_name", "user_avatar", "rank",
            "total_score", "contest_count", "member_count", "computed_at",
        ]
        read_only_fields = fields

    def get_user_avatar(self, obj):
        avatar = getattr(obj.user, "avatar", None) if obj.user else None
        if not avatar:
            return None
        request = self.context.get("request")
        url = avatar.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url
