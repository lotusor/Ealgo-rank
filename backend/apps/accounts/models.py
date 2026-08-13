from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.common.models import Platform, TimeStampedModel


class UserRole(models.TextChoices):
    """
    用户角色。个人信息页需要显式展示，所以存成字段而不是靠 group 推断。
    权限判断一律走 User.is_super_admin / is_school_admin，不要散落 role 字面量比较。
    """

    USER = "user", "普通用户"
    SCHOOL_ADMIN = "school_admin", "学校管理员"
    SUPER_ADMIN = "super_admin", "超级管理员"


class User(AbstractUser):
    """
    平台用户。
    身份认证长期会交给 lotus passport，这里预留 passport_user_id 做关联，
    本地密码登录保留用于 root 账号与 passport 不可用时的兜底。
    """

    role = models.CharField("角色", max_length=20,
                            choices=UserRole.choices, default=UserRole.USER,
                            db_index=True)
    school = models.ForeignKey("schools.School", verbose_name="所属学校",
                               null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="members")
    real_name = models.CharField("真实姓名", max_length=50, blank=True)
    student_no = models.CharField("学号", max_length=50, blank=True)

    # 统一认证中心下发的用户标识，一个 passport 用户对应一个本地账号
    passport_user_id = models.CharField("通行证用户ID", max_length=64,
                                        null=True, blank=True,
                                        unique=True, db_index=True)

    # 学校信息补全后，名下所有平台账号自动绑定到该学校（见 PlatformAccount.sync_school）
    school_bound_at = models.DateTimeField("学校绑定时间", null=True, blank=True)

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = verbose_name
        indexes = [models.Index(fields=["school", "role"])]

    def __str__(self):
        return f"{self.username}({self.get_role_display()})"

    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN or self.is_superuser

    @property
    def is_school_admin(self):
        return self.role == UserRole.SCHOOL_ADMIN

    @property
    def needs_username(self):
        """passport 首登的占位用户名尚未被用户认领。

        首登时 ``resolve_passport_user`` 用 ``passport_user_id``(UUID) 顶
        ``username``（AbstractUser 要求 username 必填且唯一）。这个占位值是
        36 位 UUID，会直接出现在个人排行榜（``ranking`` 序列化器取
        ``user.username``）和管理员审核页，所以必须引导用户在补全资料时设一个
        可读用户名。认领后即锁定，避免排行榜/审核里的身份漂移。

        本地注册用户 ``passport_user_id`` 为空，恒返回 False。
        """
        return bool(self.passport_user_id) and self.username == self.passport_user_id

    def sync_platform_accounts_school(self):
        """
        把用户当前学校同步到名下所有平台账号。
        用户填写/变更学校后必须调用，否则历史成绩仍挂在旧学校下。
        返回受影响的账号数。
        """
        return self.platform_accounts.update(school=self.school)


class PlatformAccount(TimeStampedModel):
    """
    用户在某个平台的账号。这是「成绩 -> 学生 -> 学校」归属链的唯一依据，
    我们不从比赛榜单里读学校（那些字段用户自填、缺失率高且写法混乱）。

    handle 存平台的稳定标识：
      Codeforces -> handle（大小写不敏感，统一存原样，用 handle_lower 匹配）
      AtCoder    -> UserScreenName
      牛客        -> uid（数字字符串）
    """

    user = models.ForeignKey("accounts.User", verbose_name="用户",
                             on_delete=models.CASCADE,
                             related_name="platform_accounts")
    platform = models.CharField("平台", max_length=20,
                                choices=Platform.choices, db_index=True)
    handle = models.CharField("平台账号标识", max_length=100)
    # CF handle 大小写不敏感，榜单返回的大小写不稳定，统一小写列用于匹配
    handle_lower = models.CharField("小写标识", max_length=100, db_index=True,
                                    editable=False)
    display_name = models.CharField("平台昵称", max_length=100, blank=True)

    # 冗余学校字段：排名聚合走这里，避免每次 join 到 user 再 join 到 school。
    # 由 User.sync_platform_accounts_school() 维护，不要手动改。
    school = models.ForeignKey("schools.School", verbose_name="归属学校",
                               null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="platform_accounts")

    verified = models.BooleanField("已验证归属", default=False)
    verified_at = models.DateTimeField("验证时间", null=True, blank=True)

    class Meta:
        verbose_name = "平台账号"
        verbose_name_plural = verbose_name
        constraints = [
            # 同一平台的同一账号只能被绑定一次，防止多人抢同一个 handle 刷分
            models.UniqueConstraint(fields=["platform", "handle_lower"],
                                    name="uniq_platform_handle"),
            # 同一用户在同一平台只能绑一个账号
            models.UniqueConstraint(fields=["user", "platform"],
                                    name="uniq_user_platform"),
        ]
        indexes = [models.Index(fields=["school", "platform"])]

    def __str__(self):
        return f"{self.get_platform_display()}:{self.handle}"

    def save(self, *args, **kwargs):
        self.handle_lower = (self.handle or "").strip().lower()
        # 新建时若用户已有学校，直接继承，省掉一次同步
        if self.school_id is None and self.user_id:
            self.school_id = self.user.school_id
        super().save(*args, **kwargs)


class NotificationType(models.TextChoices):
    SYSTEM = "system", "系统通知"
    APPLICATION_RECEIVED = "application_received", "管理员申请已提交"
    APPLICATION_REVIEWED = "application_reviewed", "管理员申请结果"
    ADMIN_MESSAGE = "admin_message", "管理员消息"


class Notification(TimeStampedModel):
    """
    站内信。当前用于管理员申请审批结果通知（#3），
    设计成通用结构，后续任意业务事件都能复用 notify()。
    """

    user = models.ForeignKey("accounts.User", verbose_name="接收用户",
                             on_delete=models.CASCADE,
                             related_name="notifications")
    type = models.CharField("类型", max_length=30,
                            choices=NotificationType.choices,
                            default=NotificationType.SYSTEM, db_index=True)
    title = models.CharField("标题", max_length=120)
    message = models.TextField("内容", blank=True)
    link = models.CharField("跳转链接", max_length=255, blank=True,
                            help_text="前端路由，如 /admin/applications/12")
    is_read = models.BooleanField("已读", default=False, db_index=True)
    read_at = models.DateTimeField("阅读时间", null=True, blank=True)

    class Meta:
        verbose_name = "站内信"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return f"→{self.user}:{self.title}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


def notify(user, title, message="", *, type=NotificationType.SYSTEM, link=""):
    """给某个用户发一条站内信。供各业务模块调用。"""
    return Notification.objects.create(
        user=user, title=title, message=message, type=type, link=link
    )
