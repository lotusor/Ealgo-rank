"""Crawler 相关序列化器：CrawlJob 只读展示 + 触发参数 + 自动爬取配置。"""
from rest_framework import serializers

from apps.common.platforms import crawl_choices
from apps.crawler.models import CrawlConfig, CrawlJob


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
    """手动触发一次爬取。可选平台 = 注册表里声明了爬取任务的那些。"""
    platform = serializers.ChoiceField(choices=crawl_choices())
    count = serializers.IntegerField(required=False, min_value=1, max_value=200,
                                     help_text="Codeforces/AtCoder：抓取最近 N 场")
    months = serializers.ListField(
        child=serializers.RegexField(r"^\d{4}-\d{2}$"), required=False,
        help_text="牛客：显式指定月份列表，如 ['2026-07','2026-08']")
    months_back = serializers.IntegerField(
        required=False, min_value=1, max_value=12,
        help_text="牛客：自动取最近 N 个月（与 months 互斥，months 优先）")
    force = serializers.BooleanField(
        required=False, default=False,
        help_text="跳过「只抓有已关联平台ID用户参与的比赛」预筛，"
                  "对所有 rated 免费比赛全量抓取（冷启动 / 索引重建后首次全量引导用）")


class CrawlConfigSerializer(serializers.ModelSerializer):
    """自动爬取配置（CrawlConfig 单例）。"""

    class Meta:
        model = CrawlConfig
        fields = [
            "id", "enabled", "cf_count", "atcoder_count",
            "nowcoder_months_back", "auto_crawl_interval_days",
            "auto_crawl_hour",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_auto_crawl_interval_days(self, value):
        if not 1 <= value <= 30:
            raise serializers.ValidationError("间隔天数必须在 1~30 之间")
        return value

    def validate_auto_crawl_hour(self, value):
        if not 0 <= value <= 23:
            raise serializers.ValidationError("触发小时必须在 0~23 之间")
        return value
