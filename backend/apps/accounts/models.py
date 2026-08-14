import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.accounts.security import get_security_config
from apps.common.models import Platform, TimeStampedModel


def generate_security_stamp() -> str:
    """会话吊销标记：改密/解锁/登出全部设备时轮换，使旧令牌失效。"""
    return secrets.token_hex(16)


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

    # ---------- 登录安全 ----------
    # 连续登录失败次数（成功登录清零）；达阈值由 register_login_failure 写入锁定
    failed_login_count = models.PositiveIntegerField("连续登录失败次数", default=0, db_index=True)
    # 非空表示账号临时锁定，期间禁止登录；到期（<= now）自动视为解锁
    locked_until = models.DateTimeField("锁定至", null=True, blank=True, db_index=True)
    last_failed_login_at = models.DateTimeField("最近一次失败登录", null=True, blank=True)
    # 会话吊销标记：改密/解锁/登出全部设备时轮换，使所有已签发令牌失效
    security_stamp = models.CharField("安全戳", max_length=64,
                                      default=generate_security_stamp, db_index=True)

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
    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        # 过期即视为自动解锁（无需定时任务清理）
        return self.locked_until > timezone.now()

    def register_login_failure(self):
        """记录一次失败并推进计数器；达阈值则临时锁定。"""
        now = timezone.now()
        self.failed_login_count = (self.failed_login_count or 0) + 1
        self.last_failed_login_at = now
        cfg = get_security_config()
        if self.failed_login_count >= cfg["MAX_CONSECUTIVE_FAILURES"]:
            self.locked_until = now + timedelta(
                minutes=cfg["LOCK_DURATION_MINUTES"])
        self.save(update_fields=["failed_login_count", "last_failed_login_at",
                                 "locked_until"])

    def register_login_success(self):
        """成功登录：清零失败计数与锁定。"""
        if self.failed_login_count or self.locked_until:
            self.failed_login_count = 0
            self.locked_until = None
            self.save(update_fields=["failed_login_count", "locked_until"])

    def unlock(self, rotate_stamp=True):
        """管理员手动解锁。rotate_stamp=True 时同时吊销该账号现存会话。"""
        self.locked_until = None
        self.failed_login_count = 0
        if rotate_stamp:
            self.security_stamp = generate_security_stamp()
        self.save(update_fields=["locked_until", "failed_login_count",
                                 "security_stamp"])

    def rotate_security_stamp(self):
        """轮换安全戳，使所有已签发令牌在下一次请求时被拒绝。"""
        self.security_stamp = generate_security_stamp()
        self.save(update_fields=["security_stamp"])

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

    # 参与过的比赛 external_id 列表（按平台维度，因为 handle 已平台隔离）。
    # 用于爬虫「只抓有已关联平台ID用户参与的比赛」预筛，避免下载无关全量榜单。
    # 来源：① 入库时增量更新；② rebuild_participation_index 命令从参与记录表回填 +
    #    CF/AT 官方「个人参赛历史」接口廉价补全（牛客无干净个人历史接口，仅依赖回填）。
    # 注意：这里的「用户」指所有已关联竞赛平台ID的 PlatformAccount 持有者，不限学校。
    participated_contests = models.JSONField("参与比赛索引", default=list, blank=True,
                                             help_text="该账号参与过的比赛 external_id 列表")

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


class AuthEventType(models.TextChoices):
    LOGIN_SUCCESS = "login_success", "登录成功"
    LOGIN_FAILURE = "login_failure", "登录失败"
    LOGIN_BLOCKED = "login_blocked", "登录被拦截(锁定/限流)"
    LOGOUT = "logout", "登出"
    ACCOUNT_LOCKED = "account_locked", "账号锁定"
    ACCOUNT_UNLOCKED = "account_unlocked", "账号解锁"
    ANOMALY = "anomaly", "异常行为"


class AuthLog(TimeStampedModel):
    """认证事件流：登录成功/失败、锁定/解锁、登出、异常。

    用于失败计数之外的频率限制与异常检测（撞库、登录↔登出横跳），
    以及安全审计。高频写入，可按 created_at 定期清理。
    """

    user = models.ForeignKey("accounts.User", verbose_name="用户",
                             null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="auth_logs")
    event_type = models.CharField("事件", max_length=20,
                                  choices=AuthEventType.choices, db_index=True)
    # 尝试用的标识（用户名/邮箱）；未知账号也会记录，用于按 identifier 限流
    identifier = models.CharField("尝试标识", max_length=150, blank=True, db_index=True)
    ip = models.CharField("客户端IP", max_length=64, blank=True)
    device_fp = models.CharField("设备指纹", max_length=64, blank=True, db_index=True)
    user_agent = models.TextField("User-Agent", blank=True)
    detail = models.CharField("说明", max_length=255, blank=True)

    class Meta:
        verbose_name = "认证日志"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["identifier", "created_at"]),
            models.Index(fields=["device_fp", "created_at"]),
            models.Index(fields=["ip", "created_at"]),
        ]

    def __str__(self):
        who = self.user.username if self.user else self.identifier or "?"
        return f"{self.get_event_type_display()}:{who}"
