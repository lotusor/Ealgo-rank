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
                               null=True, blank=True, on_delete=models.CASCADE,
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
        target = self.school or f"新建[{self.proposed_school_name}]"
        return f"{self.applicant} 申请 {target} 管理员 [{self.get_status_display()}]"


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

    # 只统计每个平台最近 N 场：每平台分数 = 最近 N 场的衰减加权平均。
    # 1 = 只看最新一场（原始口径）；0 = 不限场次（老场次权重随衰减自然趋零）。
    recent_contest_limit = models.PositiveIntegerField(
        "计分场次上限", default=5,
        help_text="每平台取最近 N 场的衰减加权平均；1=只看最新一场；0=不限（由衰减系数收敛）")
    # 衰减系数：最新一场权重 1，每往旧一场乘一次该系数
    # （0.85 时第 5 场权重约 0.44；1=窗口内简单平均；0=等效只看最新一场）
    rating_decay = models.DecimalField(
        "评分衰减系数", max_digits=4, decimal_places=3, default=0.850,
        help_text="0~1；越小越看重近期状态，1=窗口内平均，0=只看最新一场")
    # 新用户/新号先验 rating：作为「比全部真实场次更旧的一场」参与窗口，
    # 权重随场数衰减（1 场后约占 46%，5 场后 <11%）——同 CF 新号快收敛
    rating_prior = models.DecimalField(
        "新用户先验 Rating", max_digits=6, decimal_places=1, default=1200.0,
        help_text="站点 rating 的虚拟起点；首场后影响快速衰减")

    class Meta:
        verbose_name = "积分系数配置"
        verbose_name_plural = "积分系数配置"

    def __str__(self):
        return "全局积分配置"

    @classmethod
    def get_config(cls):
        """返回全局唯一配置；缺失则以默认参数创建。"""
        obj, _ = cls.objects.get_or_create(
            defaults={
                "cf_factor": 1.000,
                "atcoder_factor": 1.000,
                "nowcoder_factor": 1.000,
                "default_contest_factor": 1.000,
                "platform_weight": 0.500,
                "contest_weight": 0.500,
                "recent_contest_limit": 5,
                "rating_decay": 0.850,
                "rating_prior": 1200.0,
            }
        )
        return obj

    def platform_factor(self, platform):
        return {
            Platform.CODEFORCES: self.cf_factor,
            Platform.ATCODER: self.atcoder_factor,
            Platform.NOWCODER: self.nowcoder_factor,
        }.get(platform, self.default_contest_factor)


class AtCoderAffiliationAlias(TimeStampedModel):
    """AtCoder affiliation 别名归一化：把用户自填的混乱机构名映射到本校。

    仅用于人工核对（不参与积分归属，学校归属仍只认 PlatformAccount）。
    例如「Tokyo Institute of Technology」「東工大」「Tokyo Tech」都指向「东京工业大学」。
    """

    raw_affiliation = models.CharField("原始机构名", max_length=200, db_index=True,
                                        help_text="AtCoder 榜单 Affiliation 原始写法")
    school = models.ForeignKey(School, verbose_name="对应学校",
                               null=True, blank=True, on_delete=models.CASCADE,
                               related_name="affiliation_aliases")
    canonical_name = models.CharField("归一化名", max_length=200, blank=True,
                                       help_text="无对应学校时的归一化展示名")
    is_active = models.BooleanField("启用", default=True, db_index=True)
    note = models.CharField("备注", max_length=255, blank=True)

    class Meta:
        verbose_name = "AtCoder 机构别名"
        verbose_name_plural = verbose_name
        ordering = ["raw_affiliation"]
        constraints = [
            models.UniqueConstraint(fields=["raw_affiliation"],
                                    name="uniq_raw_affiliation"),
        ]

    def __str__(self):
        target = self.school.name if self.school_id else \
            (self.canonical_name or self.raw_affiliation)
        return f"{self.raw_affiliation} → {target}"


def normalize_atcoder_affiliation(raw, alias_map=None):
    """AtCoder affiliation 归一化（仅供参考，不影响归属）。

    alias_map: {lower_raw: AtCoderAffiliationAlias} 可选，命中则免查库。
    返回 dict 或 None。
    """
    if not raw:
        return None
    if alias_map is not None:
        alias = alias_map.get(raw.strip().lower())
    else:
        alias = AtCoderAffiliationAlias.objects.filter(
            raw_affiliation__iexact=raw.strip(), is_active=True).first()
    if not alias:
        return None
    return {
        "raw": alias.raw_affiliation,
        "school_id": alias.school_id,
        "school_name": alias.school.name if alias.school_id else None,
        "canonical_name": alias.canonical_name or (
            alias.school.name if alias.school_id else None),
    }


class ScoreRulePage(TimeStampedModel):
    """积分规则说明页（单例）。

    面向所有用户的「积分规则」公开页内容：
    - content 为超管在 Django admin 维护的 Markdown 说明文案；
    - 动态系数（各平台系数 / 权重 / 计分上限）由公开 API 自动拼接，
      调整系数后规则页自动同步，无需手改文案。
    """

    content = models.TextField("规则说明（Markdown）", blank=True, default="")
    version = models.PositiveIntegerField("版本号", default=1)
    updated_by = models.ForeignKey("accounts.User", verbose_name="最后编辑人",
                                   null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")

    class Meta:
        verbose_name = "积分规则页"
        verbose_name_plural = "积分规则页"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(defaults={"content": ""})
        return obj

    def __str__(self):
        return f"积分规则页 v{self.version}"
