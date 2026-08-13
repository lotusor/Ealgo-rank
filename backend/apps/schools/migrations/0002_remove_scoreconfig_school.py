from django.db import migrations


def dedupe_score_config(apps, schema_editor):
    """积分系数改为全局单例：多份配置只保留一份（优先曾经的全局默认）。"""
    ScoreConfig = apps.get_model("schools", "ScoreConfig")
    rows = list(ScoreConfig.objects.order_by("id"))
    if not rows:
        return
    keep = next((r for r in rows if r.school_id is None), rows[0])
    delete_ids = [r.id for r in rows if r.id != keep.id]
    if delete_ids:
        ScoreConfig.objects.filter(id__in=delete_ids).delete()


def reverse_noop_historical(apps, schema_editor):
    # 反向不回灌数据（字段加回后无对应数据可恢复）
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(dedupe_score_config, reverse_noop_historical),
        migrations.RemoveField(
            model_name="scoreconfig",
            name="school",
        ),
    ]
