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
