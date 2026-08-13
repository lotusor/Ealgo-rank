from django.db import models

from apps.common.models import Platform, TimeStampedModel


class School(TimeStampedModel):
    """学校。排名的聚合维度。"""

    name = models.CharField("学校名称", max_length=100, unique=True)
    short_name = models.CharField("简称", max_length=50, blank=True)
    code = models.SlugField("学校标识", max_length=50, unique=True,
                            help_text="URL 用的英文短标识，如 pku")
    logo = models.ImageField("校徽", upload_to="school_logo/", null=True, blank=True)
    description = models.TextField("简介", blank=True)
    is_active = models.BooleanField("启用", default=True, db_index=True)

    class Meta:
        verbose_name = "学校"
        verbose_name_plural = verbose_name
        ordering = ["name"]

    def __str__(self):
        return self.name


class AdminApplicationStatus(models.TextChoices):
    PENDING = "pending", "待审核"
    APPROVED = "approved", "已通过"
    REJECTED = "rejected", "已驳回"
    CANCELLED = "cancelled", "已撤回"


class SchoolAdminApplication(TimeStampedModel):
    """
    普通用户申请成为某学校管理员。
    一个学校可以有多个管理员，但同一用户对同一学校只能有一条待审记录。
    审批只由超级管理员执行。
    """

    applicant = models.ForeignKey("accounts.User", verbose_name="申请人",
                                  on_delete=models.CASCADE,
                                  related_name="admin_applications")
    school = models.ForeignKey("schools.School", verbose_name="申请学校",
                               on_delete=models.CASCADE,
                               related_name="admin_applications")
    # 允许申请系统里还没有的学校，审批通过时再建档
    proposed_school_name = models.CharField("新建学校名称", max_length=100, blank=True)
    reason = models.TextField("申请理由")
    contact = models.CharField("联系方式", max_length=100, blank=True)
    evidence = models.FileField("证明材料", upload_to="admin_apply/",
                                null=True, blank=True)

    status = models.CharField("状态", max_length=20,
                              choices=AdminApplicationStatus.choices,
                              default=AdminApplicationStatus.PENDING,
                              db_index=True)
    reviewer = models.ForeignKey("accounts.User", verbose_name="审批人",
                                 null=True, blank=True,
                                 on_delete=models.SET_NULL,
                                 related_name="reviewed_applications")
    review_comment = models.TextField("审批意见", blank=True)
    reviewed_at = models.DateTimeField("审批时间", null=True, blank=True)

    class Meta:
        verbose_name = "学校管理员申请"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["applicant", "school"],
                condition=models.Q(status="pending"),
                name="uniq_pending_application",
            ),
        ]

    def __str__(self):
        return f"{self.applicant} 申请 {self.school} 管理员 [{self.get_status_display()}]"


class ScoreConfig(TimeStampedModel):
    """
    全局唯一的积分系数配置（超管统一设置，不分学校）。
    最终积分 = 基础分 × (平台系数权重×平台系数 + 比赛系数权重×比赛难度系数)。
    """

    cf_factor = models.DecimalField("Codeforces 平台系数", max_digits=6,
                                    decimal_places=3, default=1.000)
    atcoder_factor = models.DecimalField("AtCoder 平台系数", max_digits=6,
                                         decimal_places=3, default=1.000)
    nowcoder_factor = models.DecimalField("牛客 平台系数", max_digits=6,
                                          decimal_places=3, default=0.800)

    # 比赛难度系数由 Contest.difficulty_factor 提供，这里给出兜底默认值
    default_contest_factor = models.DecimalField("比赛难度默认系数", max_digits=6,
                                                 decimal_places=3, default=1.000)
    # 平台系数与比赛系数的加权比例，两者之和应为 1
    platform_weight = models.DecimalField("平台系数权重", max_digits=4,
                                          decimal_places=3, default=0.500)
    contest_weight = models.DecimalField("比赛系数权重", max_digits=4,
                                         decimal_places=3, default=0.500)

    # 只统计每个平台最近 N 场，避免老账号靠场次堆积（0 表示不限制）
    recent_contest_limit = models.PositiveIntegerField("计分场次上限", default=0,
                                                       help_text="0 表示不限制")

    class Meta:
        verbose_name = "积分系数配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return "全局积分配置"

    @classmethod
    def get_config(cls):
        """返回全局唯一配置；缺失则以默认参数创建。"""
        obj, _ = cls.objects.get_or_create(
            defaults={
                "cf_factor": 1.000,
                "atcoder_factor": 1.000,
                "nowcoder_factor": 0.800,
                "default_contest_factor": 1.000,
                "platform_weight": 0.500,
                "contest_weight": 0.500,
                "recent_contest_limit": 0,
            }
        )
        return obj

    def platform_factor(self, platform):
        return {
            Platform.CODEFORCES: self.cf_factor,
            Platform.ATCODER: self.atcoder_factor,
            Platform.NOWCODER: self.nowcoder_factor,
        }.get(platform, self.default_contest_factor)
