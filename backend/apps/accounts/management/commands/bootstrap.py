"""
初始化命令：创建 root 超级管理员 + 全局默认积分配置。
可重复执行，已存在则跳过。

    python manage.py bootstrap
    python manage.py bootstrap --password 你的密码
"""

import secrets
import string

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User, UserRole
from apps.schools.models import ScoreConfig
from django.conf import settings


def random_password(n=16):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(n))


class Command(BaseCommand):
    help = "初始化超级管理员与全局默认积分配置"

    def add_arguments(self, parser):
        parser.add_argument("--username", default=settings.ROOT_ADMIN_USERNAME)
        parser.add_argument("--email", default=settings.ROOT_ADMIN_EMAIL)
        parser.add_argument("--password", default=None,
                            help="不传则用 ROOT_ADMIN_PASSWORD 环境变量，仍为空则随机生成并打印")
        parser.add_argument("--reset-password", action="store_true",
                            help="账号已存在时也重置密码")

    @transaction.atomic
    def handle(self, *args, **opts):
        username = opts["username"]
        password = opts["password"] or settings.ROOT_ADMIN_PASSWORD
        generated = False
        if not password:
            password = random_password()
            generated = True

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": opts["email"],
                "role": UserRole.SUPER_ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "real_name": "系统管理员",
            },
        )

        if created or opts["reset_password"]:
            user.set_password(password)
            user.role = UserRole.SUPER_ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.save()
            action = "已创建" if created else "已重置密码"
            self.stdout.write(self.style.SUCCESS(f"超级管理员 {username} {action}"))
            if generated:
                self.stdout.write(self.style.WARNING(
                    f"随机密码（仅此一次显示，请立即保存）: {password}"))
        else:
            self.stdout.write(f"超级管理员 {username} 已存在，跳过")

        config, cfg_created = ScoreConfig.objects.get_or_create(
            school=None,
            defaults={
                "cf_factor": 1.000,
                "atcoder_factor": 1.000,
                "nowcoder_factor": 0.800,
                "default_contest_factor": 1.000,
                "platform_weight": 0.500,
                "contest_weight": 0.500,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"全局积分配置{'已创建' if cfg_created else '已存在'}: {config}"))
