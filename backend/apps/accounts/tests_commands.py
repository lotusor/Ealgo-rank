from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings


class DevCommandGuardTests(TestCase):
    @override_settings(DEBUG=False)
    def test_create_test_users_refuses_outside_debug(self):
        with self.assertRaisesMessage(CommandError, "仅用于本地开发"):
            call_command("create_test_users", password="a-strong-test-password")
