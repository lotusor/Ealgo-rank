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
