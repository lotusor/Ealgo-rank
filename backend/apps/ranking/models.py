from django.db import models

from apps.common.models import Platform, TimeStampedModel


class ScoreRecord(TimeStampedModel):
    """
    单场比赛为某个学生算出的积分。积分引擎的输出，排行榜的输入。
    与 Participation 一一对应，但只对 countable 的记录生成。
    """

    participation = models.OneToOneField("contests.Participation",
                                         verbose_name="参赛记录",
                                         on_delete=models.CASCADE,
                                         related_name="score_record")
    platform_account = models.ForeignKey("accounts.PlatformAccount",
                                         verbose_name="平台账号",
                                         on_delete=models.CASCADE,
                                         related_name="score_records")
    school = models.ForeignKey("schools.School", verbose_name="学校",
                               null=True, blank=True,
                               on_delete=models.SET_NULL,
                               related_name="score_records")
    platform = models.CharField("平台", max_length=20,
                                choices=Platform.choices, db_index=True)

    base_score = models.FloatField("基础分", default=0)
    platform_factor = models.FloatField("平台系数", default=1)
    contest_factor = models.FloatField("比赛难度系数", default=1)
    final_score = models.FloatField("最终积分", default=0, db_index=True)
    formula = models.CharField("计算公式快照", max_length=255, blank=True)

    contest_time = models.DateTimeField("比赛时间", null=True, blank=True,
                                        db_index=True)

    class Meta:
        verbose_name = "积分记录"
        verbose_name_plural = verbose_name
        ordering = ["-contest_time"]
        indexes = [
            models.Index(fields=["school", "-final_score"]),
            models.Index(fields=["platform_account", "-contest_time"]),
        ]

    def __str__(self):
        return f"{self.platform_account} {self.final_score:.2f}"


class RankSnapshot(TimeStampedModel):
    """
    排行榜快照。榜单读多写少，实时聚合几十万条记录太慢，
    由 Celery 定时重算后写入这里，前端直接读。
    """

    class Scope(models.TextChoices):
        SCHOOL = "school", "学校榜"
        STUDENT = "student", "个人榜"

    scope = models.CharField("榜单类型", max_length=20,
                             choices=Scope.choices, db_index=True)
    period = models.CharField("统计周期", max_length=20, default="all",
                              help_text="all / 2026 / 2026-08 等", db_index=True)

    school = models.ForeignKey("schools.School", verbose_name="学校",
                               null=True, blank=True,
                               on_delete=models.CASCADE,
                               related_name="rank_snapshots")
    user = models.ForeignKey("accounts.User", verbose_name="用户",
                             null=True, blank=True,
                             on_delete=models.CASCADE,
                             related_name="rank_snapshots")

    rank = models.PositiveIntegerField("名次", db_index=True)
    total_score = models.FloatField("总积分", default=0)
    contest_count = models.PositiveIntegerField("参赛场次", default=0)
    member_count = models.PositiveIntegerField("统计人数", default=0,
                                               help_text="学校榜专用")
    detail = models.JSONField("明细", default=dict, blank=True)
    computed_at = models.DateTimeField("计算时间", db_index=True)

    class Meta:
        verbose_name = "排行榜快照"
        verbose_name_plural = verbose_name
        ordering = ["scope", "period", "rank"]
        indexes = [models.Index(fields=["scope", "period", "rank"])]

    def __str__(self):
        target = self.school or self.user
        return f"[{self.get_scope_display()}/{self.period}] #{self.rank} {target}"


class UserBestRecord(TimeStampedModel):
    """
    用户历史最佳纪录（学生榜 period=all 口径）。

    每次积分重算后与历史纪录比较更新：
    - best_rank 取重算历史中的最小名次，并配对达成时的总 rating；
    - best_score 取重算历史中的最高总 rating（与最佳名次不一定同一次达成）。
    系数调整会引起全量重算结果变化，纪录以「重算历史中最优」为准
    （与 CF/牛客 rating 峰值同类，接受系数变更带来的口径漂移）。
    """

    user = models.OneToOneField("accounts.User", verbose_name="用户",
                                on_delete=models.CASCADE,
                                related_name="best_record")
    best_rank = models.PositiveIntegerField("历史最佳名次")
    best_rank_score = models.FloatField("最佳名次时的总积分")
    best_rank_at = models.DateTimeField("达成最佳名次时间")
    best_score = models.FloatField("历史最高总积分")
    best_score_rank = models.PositiveIntegerField("最高总积分时的名次",
                                                  null=True, blank=True)
    best_score_at = models.DateTimeField("达成最高总积分时间")

    class Meta:
        verbose_name = "用户最佳纪录"
        verbose_name_plural = "用户最佳纪录"

    def __str__(self):
        return f"{self.user} 最佳 #{self.best_rank} / 峰值 {self.best_score:.1f}"


class Season(TimeStampedModel):
    """积分赛季（以年为单位）。

    每年一条记录：`2026` 赛季 = 2026-01-01 00:00 ~ 2026-12-31 23:59:59。
    赛季切换（年度重置）时由定时任务推进 `SeasonConfig.current_season`，
    旧赛季记录永久保留，供历史回顾。
    """

    class Stage(models.TextChoices):
        UPCOMING = "upcoming", "未开始"
        ACTIVE = "active", "进行中"
        SETTLING = "settling", "结算中"
        ENDED = "ended", "已结束"

    year = models.PositiveIntegerField("赛季编号（年份）", unique=True, db_index=True)
    name = models.CharField("赛季名称", max_length=50, default="")
    start_at = models.DateTimeField("开始时间", db_index=True)
    end_at = models.DateTimeField("结束时间", db_index=True)
    stage = models.CharField("所处阶段", max_length=20,
                             choices=Stage.choices, default=Stage.ACTIVE,
                             db_index=True)
    # 奖励内容：结构化描述，前端直接渲染；内容随赛季可不同
    rewards = models.JSONField("奖励内容", default=list, blank=True,
                               help_text="如 [{title, desc, icon}]")
    # 结算：通常是赛季结束后一个结算窗口
    settle_at = models.DateTimeField("结算时间", null=True, blank=True)

    class Meta:
        verbose_name = "积分赛季"
        verbose_name_plural = verbose_name
        ordering = ["-year"]

    def __str__(self):
        return f"{self.name or self.year} 赛季"

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"第 {self.year} 赛季"
        super().save(*args, **kwargs)


class SeasonConfig(TimeStampedModel):
    """赛季全局配置（单例）：当前赛季 + 年度重置开关。"""

    current_season = models.PositiveIntegerField("当前赛季年份", default=0)
    auto_reset = models.BooleanField("自动年度重置", default=True)

    class Meta:
        verbose_name = "赛季配置"
        verbose_name_plural = verbose_name

    @classmethod
    def get_config(cls):
        obj, _ = cls.objects.get_or_create(
            defaults={"current_season": 0, "auto_reset": True})
        return obj

    def __str__(self):
        return f"赛季配置（当前 {self.current_season or '未初始化'}）"
