"""评分衰减系数 + 计分场次默认值（滑动窗口算法上线批次）。

- 新增 ScoreConfig.rating_decay（默认 0.850）：每平台分数从「只看最新一场」
  改为「最近 N 场衰减加权平均」，decay 控制新旧权重比。
- recent_contest_limit 默认值 0→5：0（不限）语义保留，由衰减收敛；
  生产存量行需另行 UPDATE 为 5（迁移不动存量数据值）。
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0006_scorerulepage"),
    ]

    operations = [
        migrations.AddField(
            model_name="scoreconfig",
            name="rating_decay",
            field=models.DecimalField(
                decimal_places=3, default=0.85, help_text="0~1；越小越看重近期状态，1=窗口内平均，0=只看最新一场",
                max_digits=4, verbose_name="评分衰减系数"),
        ),
        migrations.AlterField(
            model_name="scoreconfig",
            name="recent_contest_limit",
            field=models.PositiveIntegerField(
                default=5, help_text="每平台取最近 N 场的衰减加权平均；1=只看最新一场；0=不限（由衰减系数收敛）",
                verbose_name="计分场次上限"),
        ),
    ]
