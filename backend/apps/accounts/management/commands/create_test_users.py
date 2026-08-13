"""为本地测试创建三类账户：普通用户、学校管理员、超级管理员。

可重复执行（已存在则跳过，除非 --reset）。

    python manage.py create_test_users
    python manage.py create_test_users --password "Test@123456"
    python manage.py create_test_users --reset
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User, UserRole
from apps.schools.models import School

DEFAULT_PASSWORD = "Test@123456"
TEST_SCHOOL_NAME = "测试大学"
TEST_SCHOOL_CODE = "testu"


class Command(BaseCommand):
    help = "创建本地测试用的普通用户 / 学校管理员 / 超级管理员账户"

    def add_arguments(self, parser):
        parser.add_argument("--password", default=DEFAULT_PASSWORD,
                            help=f"三类账户的密码（默认 {DEFAULT_PASSWORD}）")
        parser.add_argument("--reset", action="store_true",
                            help="账户已存在时也重置密码")

    @transaction.atomic
    def handle(self, *args, **opts):
        password = opts["password"]
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
            f"\n本地测试账户密码均为: {password}"))

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
