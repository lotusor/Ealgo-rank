from rest_framework import serializers

from apps.announcements.models import Announcement


class AnnouncementSerializer(serializers.ModelSerializer):
    """公告读写序列化器。超管 CRUD 与用户端公开列表共用。"""

    level_display = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = Announcement
        fields = ["id", "title", "content", "level", "level_display",
                  "pinned", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_title(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("标题不能为空")
        return value

    def validate_content(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("内容不能为空")
        return value
