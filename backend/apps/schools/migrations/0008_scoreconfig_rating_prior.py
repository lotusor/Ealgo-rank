"""v3 统一表现分：新用户先验 rating（2026-09-07）。"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0007_scoreconfig_rating_decay"),
    ]

    operations = [
        migrations.AddField(
            model_name="scoreconfig",
            name="rating_prior",
            field=models.DecimalField(
                decimal_places=1, default=1200.0,
                help_text="站点 rating 的虚拟起点；首场后影响快速衰减",
                max_digits=6, verbose_name="新用户先验 Rating"),
        ),
    ]
