from django.db import models


class TimeStampedModel(models.Model):
    """带创建/更新时间的抽象基类。业务表一律继承它。"""

    created_at = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        abstract = True


class Platform(models.TextChoices):
    """三大平台。值直接用于数据库存储与 API 传参，不要改。"""

    CODEFORCES = "codeforces", "Codeforces"
    ATCODER = "atcoder", "AtCoder"
    NOWCODER = "nowcoder", "牛客"


class ExcludeReason(models.TextChoices):
    """参赛记录被排除出积分统计的原因。"""

    NONE = "", "未排除"
    # 牛客榜单 userName 带「已被标记为作弊」前缀
    CHEATER = "cheater", "平台标记作弊"
    # 赛后补交（牛客 postContestAppend / ranking<=0，CF PRACTICE 等）
    POST_CONTEST = "post_contest", "赛后补交"
    # 未绑定到任何学生，无法归属学校
    UNBOUND = "unbound", "未绑定学生"
    # 管理员手动剔除
    MANUAL = "manual", "人工剔除"
