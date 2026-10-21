"""为本地测试创建三类账户：普通用户、学校管理员、超级管理员。

仅允许在 ``DEBUG=True`` 下执行，避免误在生产环境创建已知口令的管理员。
密码必须显式提供（命令行或 ``TEST_USER_PASSWORD`` 环境变量）。

    python manage.py create_test_users --password "<strong-random-password>"
    python manage.py create_test_users --reset --password "<strong-random-password>"
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User, UserRole
from apps.schools.models import School

TEST_SCHOOL_NAME = "测试大学"
TEST_SCHOOL_CODE = "testu"


class Command(BaseCommand):
    help = "创建本地测试用的普通用户 / 学校管理员 / 超级管理员账户（仅 DEBUG）"

    def add_arguments(self, parser):
        parser.add_argument("--password", default=None,
                            help="三类账户的密码；也可用 TEST_USER_PASSWORD 环境变量")
        parser.add_argument("--reset", action="store_true",
                            help="账户已存在时也重置密码")

    @transaction.atomic
    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError("create_test_users 仅用于本地开发；生产环境禁止执行")

        password = opts["password"] or os.environ.get("TEST_USER_PASSWORD")
        if not password:
            raise CommandError("必须通过 --password 或 TEST_USER_PASSWORD 指定测试密码")
        if len(password) < 12:
            raise CommandError("测试密码至少 12 位")
        reset = opts["reset"]

        school, school_created = School.objects.get_or_create(
            code=TEST_SCHOOL_CODE,
            defaults={"name": TEST_SCHOOL_NAME, "short_name": "测试"},
        )
        if school_created:
            self.stdout.write(self.style.SUCCESS(f"测试学校已创建: {school}"))

        # 1. 普通用户
        user, created = User.objects.get_or_create(
            username="test_user",
            defaults={
                "role": UserRole.USER,
                "email": "test_user@e-algo-rank.local",
                "real_name": "测试普通用户",
                "school": school,
            },
        )
        self._finish(user, created, reset, password)

        # 2. 学校管理员（必须归属某学校）
        admin, created = User.objects.get_or_create(
            username="test_school_admin",
            defaults={
                "role": UserRole.SCHOOL_ADMIN,
                "email": "school_admin@e-algo-rank.local",
                "real_name": "测试学校管理员",
                "school": school,
            },
        )
        if not created and admin.school_id != school.id:
            admin.school = school
            admin.save(update_fields=["school"])
        self._finish(admin, created, reset, password)

        # 3. 超级管理员
        super_user, created = User.objects.get_or_create(
            username="test_super",
            defaults={
                "role": UserRole.SUPER_ADMIN,
                "email": "super@e-algo-rank.local",
                "real_name": "测试超级管理员",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if not created and not super_user.is_superuser:
            super_user.is_staff = True
            super_user.is_superuser = True
            super_user.role = UserRole.SUPER_ADMIN
            super_user.save()
        self._finish(super_user, created, reset, password)

        self.stdout.write(self.style.WARNING(
            "\n本地测试账户已就绪；密码使用传入值，不在日志中回显。"))

    def _finish(self, user, created, reset, password):
        if created or reset:
            user.set_password(password)
            user.save()
            action = "已创建" if created else "已重置密码"
        else:
            action = "已存在，跳过"
        self.stdout.write(
            f"  - {user.get_role_display()}: {user.username} "
            f"({user.email}) {action}"
        )
