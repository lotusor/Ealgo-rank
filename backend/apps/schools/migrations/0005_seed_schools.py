"""种子学校数据：仅两项（演示用）。

演示项目学校维度只收录两所：
- 成都工业学院（code: cdut）
- chengdu technological university（code: ctu，同一学校英文名）

``get_or_create`` 保证幂等，重复 migrate 不会造重。
"""

from django.db import migrations


SEED_SCHOOLS = [
    {"name": "成都工业学院", "short_name": "成都工业学院", "code": "cdut"},
    {"name": "chengdu technological university", "short_name": "CTU", "code": "ctu"},
]


def seed_schools(apps, schema_editor):
    School = apps.get_model("schools", "School")
    for s in SEED_SCHOOLS:
        School.objects.get_or_create(name=s["name"], defaults=dict(s))


def revert_schools(apps, schema_editor):
    School = apps.get_model("schools", "School")
    School.objects.filter(
        name__in=[s["name"] for s in SEED_SCHOOLS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0004_atcoderaffiliationalias"),
    ]

    operations = [
        migrations.RunPython(seed_schools, revert_schools),
    ]
