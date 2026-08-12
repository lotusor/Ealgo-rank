"""Crawler 相关序列化器：CrawlJob 只读展示 + 触发参数。"""
from rest_framework import serializers

from apps.crawler.models import CrawlJob
from apps.common.models import Platform


class CrawlJobSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(
        source="get_platform_display", read_only=True)
    status_display = serializers.CharField(
        source="get_status_display", read_only=True)
    triggered_by_name = serializers.CharField(
        source="triggered_by.username", read_only=True, default="")
    duration_seconds = serializers.FloatField(read_only=True)

    class Meta:
        model = CrawlJob
        fields = [
            "id", "platform", "platform_display", "status", "status_display",
            "triggered_by", "triggered_by_name", "params", "celery_task_id",
            "started_at", "finished_at", "duration_seconds",
            "contest_count", "participation_count", "cheater_count",
            "error_message", "log", "created_at",
        ]
        read_only_fields = fields


class CrawlTriggerSerializer(serializers.Serializer):
    """手动触发一次爬取。"""
    PLATFORM_CHOICES = (
        (Platform.CODEFORCES, "Codeforces"),
        (Platform.ATCODER, "AtCoder"),
        (Platform.NOWCODER, "牛客"),
    )
    platform = serializers.ChoiceField(choices=PLATFORM_CHOICES)
    count = serializers.IntegerField(required=False, min_value=1, max_value=200,
                                     help_text="Codeforces/AtCoder：抓取最近 N 场")
    months = serializers.ListField(
        child=serializers.RegexField(r"^\d{4}-\d{2}$"), required=False,
        help_text="牛客：显式指定月份列表，如 ['2026-07','2026-08']")
    months_back = serializers.IntegerField(
        required=False, min_value=1, max_value=12,
        help_text="牛客：自动取最近 N 个月（与 months 互斥，months 优先）")
