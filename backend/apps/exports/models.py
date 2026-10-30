"""「导出学校赛情」的任务与审计模型。

三处刻意的设计取舍（改之前请先读这段）：

1. **状态落库，不用 Celery 的 `AsyncResult`。** 本仓没有 `update_state` 先例，
   且 Redis 结果后端会过期；导出凭据必须长期可查、可审计。
   范式与 `crawler.CrawlJob` 一致。

2. **`scope_school_ids` 是创建时的快照，不是外键集合。** 导出是一次性凭据，
   事后再有学校新增/停用/合并，不应该改变已生成文件的口径——否则同一份
   报表隔天重下内容就变了，无法对账。

3. **一个 actor 同时只允许一个 pending/running 任务，用部分唯一索引在 DB 层
   兜住**（不依赖 Redis：Redis 抖动时数据库仍然是最终裁判）。
   SQLite 与 PostgreSQL 都支持部分唯一索引，CI 不会因此变红。
"""
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class ExportJob(TimeStampedModel):
    """一次「导出学校赛情」的完整记录。"""

    class Status(models.TextChoices):
        PENDING = "pending", "排队中"
        RUNNING = "running", "生成中"
        SUCCEEDED = "succeeded", "已完成"
        FAILED = "failed", "失败"
        EXPIRED = "expired", "已过期"
        REVOKED = "revoked", "已撤销"

    class ScopeKind(models.TextChoices):
        SCHOOL = "school", "单校"
        MULTI = "multi", "多校"
        ALL = "all", "全站"

    class Layout(models.TextChoices):
        PER_SCHOOL = "per_school", "按校拆分"
        MERGED = "merged", "合并单表"

    actor = models.ForeignKey(
        "accounts.User", verbose_name="操作人", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="export_jobs",
        help_text="留空表示账号已注销；审计仍需保留任务记录")
    # 创建时的角色快照：事后 actor 被降级也能看出「当时凭什么导出全站」
    actor_role = models.CharField("操作人角色", max_length=20, blank=True)

    scope_kind = models.CharField("范围类型", max_length=10,
                                  choices=ScopeKind.choices)
    scope_school_ids = models.JSONField("范围学校ID快照", default=list,
                                        blank=True)
    year = models.PositiveIntegerField("赛季年份", db_index=True)
    layout = models.CharField("输出形态", max_length=20,
                              choices=Layout.choices,
                              default=Layout.PER_SCHOOL)
    options = models.JSONField("其他选项", default=dict, blank=True)
    fingerprint = models.CharField("参数指纹", max_length=32, blank=True,
                                   db_index=True,
                                   help_text="含 actor_id，用于幂等复用")

    status = models.CharField("状态", max_length=20, choices=Status.choices,
                              default=Status.PENDING, db_index=True)
    celery_task_id = models.CharField("Celery 任务ID", max_length=64,
                                      blank=True, db_index=True)

    row_count = models.PositiveIntegerField("数据行数", default=0)
    sheet_count = models.PositiveIntegerField("工作表数", default=0)

    file_name = models.CharField("下载文件名", max_length=255, blank=True)
    file_path = models.CharField("落盘路径", max_length=500, blank=True,
                                 help_text="相对 EXPORT_ROOT 的文件名")
    file_size = models.PositiveBigIntegerField("文件字节数", default=0)
    checksum = models.CharField("SHA256", max_length=64, blank=True)

    expires_at = models.DateTimeField("过期时间", null=True, blank=True,
                                      db_index=True)
    download_count = models.PositiveIntegerField("下载次数", default=0)
    last_download_at = models.DateTimeField("最近下载时间", null=True,
                                            blank=True)
    suspicious = models.BooleanField("异常下载标记", default=False,
                                     db_index=True)

    ip = models.GenericIPAddressField("来源IP", null=True, blank=True)
    device_fp = models.CharField("设备指纹", max_length=64, blank=True)
    user_agent = models.CharField("User-Agent", max_length=255, blank=True)

    error_message = models.TextField("错误信息", blank=True)
    started_at = models.DateTimeField("开始生成时间", null=True, blank=True)
    finished_at = models.DateTimeField("结束时间", null=True, blank=True)

    class Meta:
        verbose_name = "导出任务"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        constraints = [
            # 同一个操作人同时只能有一个未完成任务。并发双击由 DB 拒绝，
            # 不靠 Redis 锁（Redis 不可用时仍要保证唯一）。
            models.UniqueConstraint(
                fields=["actor"],
                condition=models.Q(status__in=["pending", "running"]),
                name="uniq_active_export_per_actor",
            ),
        ]
        indexes = [
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"导出 #{self.pk} [{self.get_status_display()}]"

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= timezone.now())

    @property
    def is_downloadable(self) -> bool:
        return (self.status == self.Status.SUCCEEDED
                and not self.is_expired and bool(self.file_path))


class ExportEvent(models.TextChoices):
    """导出相关的四类留痕事件。"""

    CREATE = "create", "创建"
    DOWNLOAD = "download", "下载"
    REVOKE = "revoke", "撤销"
    DENIED = "denied", "越权拒绝"


class ExportAuditLog(models.Model):
    """导出的 append-only 留痕。

    与 `accounts.HandleAudit` 同一定位：只增不改，admin 里禁止编辑。
    **不写学生姓名/学号**——审计是排查用的，不是第二个 PII 副本。
    """

    job_id_snapshot = models.PositiveBigIntegerField("任务ID快照", null=True,
                                                     blank=True, db_index=True,
                                                     help_text="任务被清理后仍可追溯")
    actor = models.ForeignKey("accounts.User", verbose_name="操作人",
                              null=True, blank=True,
                              on_delete=models.SET_NULL,
                              related_name="export_audit_logs")
    actor_username = models.CharField("操作人账号快照", max_length=150,
                                      blank=True)
    event = models.CharField("事件", max_length=20, choices=ExportEvent.choices,
                             db_index=True)
    reason = models.CharField("原因码", max_length=64, blank=True,
                              help_text="denied 时的拒绝原因，如 school_mismatch")
    detail = models.JSONField("明细", default=dict, blank=True,
                              help_text="只放范围/年份等参数，不含学生个人信息")
    ip = models.GenericIPAddressField("来源IP", null=True, blank=True)
    device_fp = models.CharField("设备指纹", max_length=64, blank=True)
    user_agent = models.CharField("User-Agent", max_length=255, blank=True)
    created_at = models.DateTimeField("时间", auto_now_add=True,
                                      db_index=True)

    class Meta:
        verbose_name = "导出留痕"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "event", "-created_at"]),
            models.Index(fields=["ip", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.get_event_display()} {self.actor_username or '-'} #{self.job_id_snapshot}"
