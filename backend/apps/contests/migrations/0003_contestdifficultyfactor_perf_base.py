"""v3 统一表现分：难度基线 D 与新用户先验（2026-09-07）。

- contests.ContestDifficultyFactor.perf_base：难度基线覆盖位（null=代码默认表）
- schools.ScoreConfig.rating_prior：新用户先验 rating（默认 1200）
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contests", "0002_contestdifficultyfactor"),
    ]

    operations = [
        migrations.AddField(
            model_name="contestdifficultyfactor",
            name="perf_base",
            field=models.FloatField(
                blank=True, help_text="rating 尺度；留空用代码默认表。示例：CF Div.2≈1450 / ABC≈800 / ARC≈1550 / 牛客周赛≈950",
                null=True, verbose_name="难度基线 D（表现分）"),
        ),
    ]
