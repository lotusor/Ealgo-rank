from django.db import models

from apps.common.models import ExcludeReason, Platform, TimeStampedModel


class Contest(TimeStampedModel):
    """
    一场比赛。只收录 rated 且免费的比赛（爬虫层已过滤，这里再存一份判定依据便于审计）。
    """

    platform = models.CharField("平台", max_length=20,
                                choices=Platform.choices, db_index=True)
    # 平台侧的比赛标识：CF 为 contestId，AtCoder 为 contest id（如 abc469），
    # 牛客为详情页 URL 里的 id（注意不是日历接口的 contestId）
    external_id = models.CharField("平台比赛ID", max_length=64, db_index=True)
    name = models.CharField("比赛名称", max_length=255)
    url = models.URLField("比赛链接", max_length=500, blank=True)

    start_time = models.DateTimeField("开始时间", null=True, blank=True, db_index=True)
    end_time = models.DateTimeField("结束时间", null=True, blank=True)
    duration_minutes = models.PositiveIntegerField("时长（分钟）", null=True, blank=True)

    # ---- rated / 收费判定，与爬虫输出字段一一对应 ----
    is_rated = models.BooleanField("计入平台 rating", default=False, db_index=True)
    is_paid = models.BooleanField("付费比赛", default=False, db_index=True)
    rated_source = models.CharField("判定来源", max_length=100, blank=True)
    rated_comment = models.CharField("判定说明", max_length=255, blank=True)
    series = models.CharField("赛事系列", max_length=100, blank=True,
                              help_text="如 牛客周赛 / Div.2")

    # 比赛难度系数，学校管理员可调，参与积分加权
    difficulty_factor = models.DecimalField("比赛难度系数", max_digits=6,
                                            decimal_places=3, default=1.000)

    problem_count = models.PositiveIntegerField("题目数", default=0)
    participant_count = models.PositiveIntegerField("参赛人数", default=0)
    # 排除作弊与赛后补交之后，真正计入积分的人数
    valid_participant_count = models.PositiveIntegerField("有效参赛人数", default=0)
    cheater_count = models.PositiveIntegerField("作弊账号数", default=0)

    raw_meta = models.JSONField("原始元数据", default=dict, blank=True)
    crawled_at = models.DateTimeField("最近抓取时间", null=True, blank=True)

    class Meta:
        verbose_name = "比赛"
        verbose_name_plural = verbose_name
        ordering = ["-start_time"]
        constraints = [
            models.UniqueConstraint(fields=["platform", "external_id"],
                                    name="uniq_platform_contest"),
        ]
        indexes = [
            models.Index(fields=["platform", "-start_time"]),
            models.Index(fields=["is_rated", "is_paid"]),
        ]

    def __str__(self):
        return f"[{self.get_platform_display()}] {self.name}"

    @property
    def countable(self):
        """是否应计入积分：rated 且非付费。"""
        return self.is_rated and not self.is_paid


class Problem(TimeStampedModel):
    """比赛题目。CF 从 problemset.problems 索引取，不下载整场 standings。"""

    contest = models.ForeignKey(Contest, verbose_name="比赛",
                                on_delete=models.CASCADE, related_name="problems")
    index = models.CharField("题号", max_length=10, help_text="A/B/C...")
    title = models.CharField("题目名", max_length=255, blank=True)
    external_id = models.CharField("平台题目ID", max_length=64, blank=True)
    full_score = models.IntegerField("满分", null=True, blank=True)
    solved_count = models.PositiveIntegerField("通过人数", default=0)
    raw = models.JSONField("原始数据", default=dict, blank=True)

    class Meta:
        verbose_name = "题目"
        verbose_name_plural = verbose_name
        ordering = ["contest", "index"]
        constraints = [
            models.UniqueConstraint(fields=["contest", "index"],
                                    name="uniq_contest_problem"),
        ]

    def __str__(self):
        return f"{self.contest.name} {self.index}"


class ParticipationQuerySet(models.QuerySet):
    def countable(self):
        """
        可计入积分的参赛记录。
        这是积分引擎唯一允许的入口，任何聚合都必须从这里出发，
        避免哪天漏判把作弊账号算进学校总分。
        """
        return self.filter(
            is_excluded=False,
            platform_account__isnull=False,
            contest__is_rated=True,
            contest__is_paid=False,
        )

    def for_school(self, school_id):
        return self.filter(platform_account__school_id=school_id)


class Participation(TimeStampedModel):
    """
    某个平台账号在某场比赛的成绩。
    榜单里绝大多数人跟我们无关，只有能匹配到 PlatformAccount 的才建记录 —— 
    但作弊账号是例外：即便匹配上了也要落库并标记，便于管理员追溯与申诉。
    """

    contest = models.ForeignKey(Contest, verbose_name="比赛",
                                on_delete=models.CASCADE,
                                related_name="participations")
    # 匹配不到已注册学生时为空，此类记录不参与积分（见 countable）
    platform_account = models.ForeignKey("accounts.PlatformAccount",
                                         verbose_name="平台账号",
                                         null=True, blank=True,
                                         on_delete=models.SET_NULL,
                                         related_name="participations")
    # 榜单原始标识，即使没绑定学生也留着，等学生后续注册时可回填
    handle = models.CharField("榜单账号标识", max_length=100, db_index=True)
    handle_lower = models.CharField("小写标识", max_length=100, db_index=True,
                                    editable=False)
    display_name = models.CharField("榜单昵称", max_length=150, blank=True)

    rank = models.IntegerField("名次", null=True, blank=True, db_index=True)
    solved_count = models.IntegerField("过题数", null=True, blank=True)
    total_score = models.FloatField("总分", null=True, blank=True)
    penalty_ms = models.BigIntegerField("罚时（毫秒）", null=True, blank=True)
    rating_delta = models.IntegerField("rating 变化", null=True, blank=True)
    old_rating = models.IntegerField("赛前 rating", null=True, blank=True)
    new_rating = models.IntegerField("赛后 rating", null=True, blank=True)

    # ---- 排除标记：作弊、赛后补交等 ----
    is_excluded = models.BooleanField("排除出积分", default=False, db_index=True)
    exclude_reason = models.CharField("排除原因", max_length=20,
                                      choices=ExcludeReason.choices,
                                      blank=True, default="")
    # 牛客作弊账号的原始 userName（带「已被标记为作弊」前缀），保留供审计
    raw_display_name = models.CharField("原始昵称", max_length=200, blank=True)

    score_detail = models.JSONField("每题明细", default=list, blank=True)
    extra = models.JSONField("平台特有字段", default=dict, blank=True)

    class Meta:
        verbose_name = "参赛记录"
        verbose_name_plural = verbose_name
        ordering = ["contest", "rank"]
        constraints = [
            models.UniqueConstraint(fields=["contest", "handle_lower"],
                                    name="uniq_contest_handle"),
        ]
        indexes = [
            models.Index(fields=["platform_account", "-created_at"]),
            models.Index(fields=["is_excluded", "contest"]),
        ]

    objects = ParticipationQuerySet.as_manager()

    def __str__(self):
        flag = f" [{self.get_exclude_reason_display()}]" if self.is_excluded else ""
        return f"{self.handle}@{self.contest.name} #{self.rank}{flag}"

    def save(self, *args, **kwargs):
        self.handle_lower = (self.handle or "").strip().lower()
        # 排除标记与原因必须同进同出，避免出现「标记了但没原因」的脏数据
        if self.is_excluded and not self.exclude_reason:
            self.exclude_reason = ExcludeReason.MANUAL
        if not self.is_excluded:
            self.exclude_reason = ""
        super().save(*args, **kwargs)
