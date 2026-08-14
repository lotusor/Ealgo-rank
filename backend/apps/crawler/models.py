from django.db import models

from apps.common.models import Platform, TimeStampedModel


class CrawlJob(TimeStampedModel):
    """
    一次爬取任务的记录。管理员手动触发或 Celery Beat 定时产生，
    出问题时靠这张表定位是哪次抓取污染了数据。
    """

    class Status(models.TextChoices):
        PENDING = "pending", "排队中"
        RUNNING = "running", "执行中"
        SUCCESS = "success", "成功"
        FAILED = "failed", "失败"
        PARTIAL = "partial", "部分成功"

    platform = models.CharField("平台", max_length=20,
                                choices=Platform.choices, db_index=True)
    status = models.CharField("状态", max_length=20, choices=Status.choices,
                              default=Status.PENDING, db_index=True)
    triggered_by = models.ForeignKey("accounts.User", verbose_name="触发人",
                                     null=True, blank=True,
                                     on_delete=models.SET_NULL,
                                     related_name="crawl_jobs",
                                     help_text="留空表示定时任务")
    params = models.JSONField("任务参数", default=dict, blank=True,
                              help_text="如 months / contest_ids")
    celery_task_id = models.CharField("Celery 任务ID", max_length=64,
                                      blank=True, db_index=True)

    started_at = models.DateTimeField("开始时间", null=True, blank=True)
    finished_at = models.DateTimeField("结束时间", null=True, blank=True)

    contest_count = models.PositiveIntegerField("处理比赛数", default=0)
    participation_count = models.PositiveIntegerField("入库记录数", default=0)
    cheater_count = models.PositiveIntegerField("排除作弊数", default=0)
    error_message = models.TextField("错误信息", blank=True)
    log = models.TextField("执行日志", blank=True)

    class Meta:
        verbose_name = "爬取任务"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_platform_display()}] {self.get_status_display()} #{self.pk}"

    @property
    def duration_seconds(self):
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class CrawlConfig(TimeStampedModel):
    """
    自动爬取的全局配置（超管统一设置，单例）。

    - enabled：是否启用定时自动爬取（对应「设置定时任务自动激活爬虫」）
    - cf_count / atcoder_count：Codeforces / AtCoder 每次抓取最近 N 场
    - nowcoder_months_back：牛客抓取最近 N 个月
    - auto_crawl_hour：每日自动触发的小时（0-23），分钟固定为 00
    """

    enabled = models.BooleanField("启用自动爬取", default=True,
                                  help_text="关闭后即便 beat 到点也不会触发爬取")
    cf_count = models.PositiveIntegerField("Codeforces 抓取场数", default=20,
                                           help_text="最近 N 场（rated）")
    atcoder_count = models.PositiveIntegerField("AtCoder 抓取场数", default=20,
                                                help_text="最近 N 场（rated）")
    nowcoder_months_back = models.PositiveIntegerField("牛客最近月数", default=2,
                                                       help_text="抓取最近 N 个月的比赛")
    auto_crawl_hour = models.PositiveIntegerField("自动爬取小时", default=2,
                                                  help_text="每日该小时(0-23)触发，分钟固定 00")

    class Meta:
        verbose_name = "自动爬取配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"自动爬取配置（{'启用' if self.enabled else '停用'}）"

    @classmethod
    def get_config(cls):
        """返回全局唯一配置；缺失则以默认参数创建。"""
        obj, _ = cls.objects.get_or_create(
            defaults={
                "enabled": True,
                "cf_count": 20,
                "atcoder_count": 20,
                "nowcoder_months_back": 2,
                "auto_crawl_hour": 2,
            }
        )
        return obj
