from django.db import models

from apps.common.models import TimeStampedModel


class AnnouncementLevel(models.TextChoices):
    """公告级别，决定前端顶栏左侧色条与图标语义。值直接进 API/前端，勿改。"""

    INFO = "info", "普通"
    SUCCESS = "success", "成功"
    WARNING = "warning", "警告"
    DANGER = "danger", "重要"


class Announcement(TimeStampedModel):
    """
    系统公告。用户端顶栏轮播展示（SystemAnnouncement.vue），仅超管可发布/编辑/删除。

    与 Notification（按用户的私信、带已读状态）是两套语义：公告是全局广播，
    无接收人/已读概念，所以独立成表而不是复用 Notification。
    """

    title = models.CharField("标题", max_length=120)
    content = models.TextField("内容")
    level = models.CharField(
        "级别", max_length=10, choices=AnnouncementLevel.choices,
        default=AnnouncementLevel.INFO, db_index=True,
    )
    pinned = models.BooleanField(
        "置顶", default=False, db_index=True,
        help_text="置顶公告始终排在最前",
    )
    is_active = models.BooleanField(
        "启用", default=True, db_index=True,
        help_text="关闭后用户端不再展示，但记录保留可随时重新启用",
    )

    class Meta:
        verbose_name = "系统公告"
        verbose_name_plural = verbose_name
        ordering = ["-pinned", "-updated_at"]

    def __str__(self):
        return f"{self.get_level_display()}:{self.title}"
