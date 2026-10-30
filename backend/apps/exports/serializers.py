"""导出接口的序列化器。

职责边界：**只校验形状，不判权限**。范围与权限归一化在 views 里做，
因为拒绝时需要同时写 `denied` 审计，而序列化器拿不到完整上下文。
"""
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from apps.exports.models import ExportJob
from apps.exports.services import default_year

MAX_SCHOOLS = 200
LAYOUT_CHOICES = [ExportJob.Layout.PER_SCHOOL, ExportJob.Layout.MERGED]
RATING_WINDOW_CHOICES = ["season", "latest"]


class ExportCreateSerializer(serializers.Serializer):
    scope_kind = serializers.ChoiceField(choices=ExportJob.ScopeKind.choices)
    school_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False, allow_empty=True, default=list,
        max_length=MAX_SCHOOLS,
    )
    year = serializers.IntegerField(required=False)
    layout = serializers.ChoiceField(choices=LAYOUT_CHOICES,
                                     default=ExportJob.Layout.PER_SCHOOL)
    include_zero_participation = serializers.BooleanField(default=False)
    include_global_rank = serializers.BooleanField(default=True)
    rating_window = serializers.ChoiceField(choices=RATING_WINDOW_CHOICES,
                                            default="season")

    def validate_year(self, value):
        """年份白名单：任意整数会让查询扫全表，也会污染幂等指纹。"""
        current = timezone.localdate().year
        low = settings.EXPORT_MIN_YEAR
        if value < low or value > current + 1:
            raise serializers.ValidationError(
                f"赛季年份需在 {low}–{current + 1} 之间")
        return value

    def validate(self, attrs):
        year = attrs.get("year") or default_year()
        attrs["year"] = year

        kind = attrs["scope_kind"]
        ids = attrs.get("school_ids") or []
        ids = list(dict.fromkeys(ids))  # 去重且保序
        if len(ids) > MAX_SCHOOLS:
            raise serializers.ValidationError(
                {"school_ids": f"一次最多选择 {MAX_SCHOOLS} 所学校"})
        if kind == ExportJob.ScopeKind.SCHOOL and len(ids) != 1:
            raise serializers.ValidationError(
                {"school_ids": "单选形态需要且仅需要一个学校"})
        if kind == ExportJob.ScopeKind.MULTI and not ids:
            raise serializers.ValidationError(
                {"school_ids": "多选形态至少需要一个学校"})
        if kind == ExportJob.ScopeKind.ALL and ids:
            raise serializers.ValidationError(
                {"school_ids": "全站形态不接受 school_ids"})
        attrs["school_ids"] = ids
        return attrs


class ExportJobSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display",
                                           read_only=True)
    scope_kind_display = serializers.CharField(source="get_scope_kind_display",
                                               read_only=True)
    layout_display = serializers.CharField(source="get_layout_display",
                                           read_only=True)
    actor_username = serializers.CharField(source="actor.username",
                                            read_only=True, default="")
    download_url = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = ExportJob
        fields = [
            "id", "status", "status_display", "scope_kind",
            "scope_kind_display", "scope_school_ids", "year", "layout",
            "layout_display", "options",
            "row_count", "sheet_count", "file_name", "file_size",
            "download_count", "is_expired", "expires_at", "suspicious",
            "error_message", "actor_username",
            "created_at", "started_at", "finished_at", "download_url",
        ]
        read_only_fields = fields

    def get_download_url(self, obj):
        if not obj.is_downloadable:
            return None
        return f"/api/v1/exports/{obj.pk}/download/"
