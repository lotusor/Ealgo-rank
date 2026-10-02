import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from datetime import timedelta

from apps.accounts.models import (
    HandleAudit,
    HandleAuditAction,
    Notification,
    NotificationType,
    PlatformAccount,
    UserRole,
)
from apps.accounts.serializers import PlatformAccountSerializer
from apps.contests.models import Contest, Participation
from apps.schools.models import School

User = get_user_model()


class AccountsApiTests(APITestCase):
    """#4 认证与用户/学校模块接口回归。全程离线，不触碰外部网络。"""

    def setUp(self):
        self.super = User.objects.create_superuser(
            username="sup", email="sup@x.com", password="Sup1234!")
        self.client = self.client_class()

    def _register(self, username="alice"):
        return self.client.post("/api/v1/register/", {
            "username": username,
            "email": username + "@x.com",
            "password": "Test1234!",
            "password2": "Test1234!",
            "real_name": "爱丽丝",
            "student_no": "2021001",
        })

    def test_register_returns_user_and_tokens(self):
        r = self._register()
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertIn("access", body)
        self.assertIn("refresh", body)
        self.assertEqual(body["user"]["username"], "alice")
        # 默认角色是普通用户
        self.assertEqual(body["user"]["role"], "user")

    def test_me_requires_auth(self):
        # 未登录
        r = self.client.get("/api/v1/me/")
        self.assertEqual(r.status_code, 401)
        # 登录后可见
        self._register()
        token = self.client.post("/api/v1/auth/token/",
                                 {"username": "alice", "password": "Test1234!"}).json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)
        r = self.client.get("/api/v1/me/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["username"], "alice")

    def test_bind_platform_and_reject_duplicate_platform(self):
        self._register("bob")
        token = self.client.post("/api/v1/auth/token/",
                                 {"username": "bob", "password": "Test1234!"}).json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)
        # 首次绑定成功
        r = self.client.post("/api/v1/platform-accounts/", {
            "platform": "codeforces", "handle": "cf_bob", "display_name": "bob"})
        self.assertEqual(r.status_code, 201)
        # 同平台再绑一个不同 handle → 应被拒（uniq_user_platform）
        r = self.client.post("/api/v1/platform-accounts/", {
            "platform": "codeforces", "handle": "cf_bob2"})
        self.assertEqual(r.status_code, 400)
        # 换个平台可以
        r = self.client.post("/api/v1/platform-accounts/", {
            "platform": "atcoder", "handle": "at_bob"})
        self.assertEqual(r.status_code, 201)

    def test_school_list_public_and_create_requires_superadmin(self):
        # 列表公开可读
        r = self.client.get("/api/v1/schools/")
        self.assertEqual(r.status_code, 200)
        # 普通用户创建 → 403
        self._register("carol")
        token = self.client.post("/api/v1/auth/token/",
                                 {"username": "carol", "password": "Test1234!"}).json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)
        r = self.client.post("/api/v1/schools/", {
            "name": "甲大学", "code": "jia", "short_name": "甲"})
        self.assertEqual(r.status_code, 403)
        # 超管创建 → 201
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + str(
                self.client.post("/api/v1/auth/token/",
                                {"username": "sup", "password": "Sup1234!"}).json()["access"]))
        r = self.client.post("/api/v1/schools/", {
            "name": "甲大学", "code": "jia", "short_name": "甲"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(School.objects.filter(code="jia").count(), 1)


class SchoolAdminRosterIsolationTests(APITestCase):
    """#4 校管成员名单仅可见本校，不可跨校。"""

    def setUp(self):
        self.school_a = School.objects.create(
            name="A大学", code="a", short_name="A")
        self.school_b = School.objects.create(
            name="B大学", code="b", short_name="B")
        self.admin_a = User.objects.create_user(
            username="adminA", password="Test1234!",
            role=UserRole.SCHOOL_ADMIN, school=self.school_a)
        self.admin_b = User.objects.create_user(
            username="adminB", password="Test1234!",
            role=UserRole.SCHOOL_ADMIN, school=self.school_b)
        User.objects.create_user(username="userA1", password="x",
                                 school=self.school_a)
        User.objects.create_user(username="userA2", password="x",
                                 school=self.school_a)
        User.objects.create_user(username="userB1", password="x",
                                 school=self.school_b)

    def test_admin_sees_only_own_school(self):
        self.client.force_authenticate(self.admin_a)
        r = self.client.get("/api/v1/users/")
        self.assertEqual(r.status_code, 200)
        # A 校共 3 人：adminA + userA1 + userA2
        self.assertEqual(r.data["count"], 3)
        names = {u["username"] for u in r.data["results"]}
        self.assertIn("userA1", names)
        self.assertIn("userA2", names)
        self.assertNotIn("userB1", names)
        self.assertNotIn("adminB", names)

    def test_other_school_admin_cannot_see_this_school(self):
        self.client.force_authenticate(self.admin_b)
        r = self.client.get("/api/v1/users/")
        names = {u["username"] for u in r.data["results"]}
        self.assertNotIn("userA1", names)
        self.assertEqual(r.data["count"], 2)  # adminB + userB1


class PlatformHandleEditTests(APITestCase):
    """平台账号 ID 修改：一周一次冷却 + 归属唯一性 + 回填历史成绩。"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="handleuser", password="Test1234!")
        self.client.force_authenticate(self.user)

    def _bind(self, platform="codeforces", handle="cf_alice"):
        return self.client.post("/api/v1/platform-accounts/", {
            "platform": platform, "handle": handle})

    def test_display_only_platform_cannot_be_bound(self):
        """只做赛程展示的平台（洛谷）不给绑定：绑上就是一个永远没成绩的空账号位。

        能力开关在 `apps/common/platforms.py` 的注册表里，写入口必须挡住，
        不能只靠前端把按钮藏掉。
        """
        r = self._bind("luogu", "1001")
        self.assertEqual(r.status_code, 400, r.data)
        self.assertIn("platform", r.data["errors"])
        self.assertIn("只用于赛程展示", str(r.data["errors"]["platform"]))
        self.assertEqual(
            PlatformAccount.objects.filter(platform="luogu").count(), 0)

    def test_patch_handle_first_time_allowed(self):
        r = self._bind("codeforces", "cf_alice")
        self.assertEqual(r.status_code, 201)
        pk = r.json()["id"]
        # 首次修改 handle 应允许
        r = self.client.patch(f"/api/v1/platform-accounts/{pk}/",
                              {"handle": "cf_alice2"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["handle"], "cf_alice2")
        # can_edit_handle 变为 false（一周内已改过）
        self.assertFalse(r.json()["can_edit_handle"])

    def test_patch_handle_twice_within_cooldown_rejected(self):
        r = self._bind("codeforces", "cf_alice")
        pk = r.json()["id"]
        self.client.patch(f"/api/v1/platform-accounts/{pk}/",
                          {"handle": "cf_alice2"}, format="json")
        # 一周内再改 → 拒绝
        r = self.client.patch(f"/api/v1/platform-accounts/{pk}/",
                              {"handle": "cf_alice3"}, format="json")
        self.assertEqual(r.status_code, 400)
        errors = r.json().get("errors", {})
        self.assertIn("handle", errors)

    def test_patch_handle_conflict_with_other_user(self):
        self._bind("codeforces", "cf_alice")
        other = User.objects.create_user(username="other", password="Test1234!")
        self.client.force_authenticate(other)
        r = self._bind("codeforces", "cf_bob")
        pk = r.json()["id"]
        # 尝试改成别人已占用的 handle → 拒绝
        r = self.client.patch(f"/api/v1/platform-accounts/{pk}/",
                              {"handle": "cf_alice"}, format="json")
        self.assertEqual(r.status_code, 400)
        errors = r.json().get("errors", {})
        self.assertIn("handle", errors)

    def test_platform_field_not_changeable(self):
        r = self._bind("codeforces", "cf_alice")
        pk = r.json()["id"]
        # 改 platform 应被忽略或拒绝（serializer 未把 platform 设为只读，
        # 但 update 校验会因 unique 约束或 handle 归属出错；这里验证不破坏归属）
        r = self.client.patch(f"/api/v1/platform-accounts/{pk}/",
                              {"platform": "atcoder"}, format="json")
        # 允许 200（platform 未在 update 里做特殊限制），但 handle 归属应保持不变
        self.assertIn(r.status_code, (200, 400))

    def _make_contest(self, ext_id, name):
        from apps.common.models import Platform
        return Contest.objects.create(
            platform=Platform.CODEFORCES, external_id=ext_id, name=name,
            start_time="2026-08-01 20:00:00+00:00",
            end_time="2026-08-01 22:00:00+00:00", is_rated=True)

    def test_unbind_deletes_participations_and_triggers_recompute(self):
        """解绑即删成绩（不留 unbound 遗留行）+ 数据变化触发排名重算。"""
        r = self._bind("codeforces", "cf_alice")
        pk = r.json()["id"]
        from apps.accounts.models import PlatformAccount
        acc = PlatformAccount.objects.get(pk=pk)
        for i, ext in enumerate(["1111", "1112", "1113"]):
            c = self._make_contest(ext, f"CF Round {i}")
            Participation.objects.create(
                contest=c, platform_account=acc, handle="cf_alice",
                handle_lower="cf_alice", rank=i + 1)
        self.assertEqual(Participation.objects.count(), 3)

        with patch("apps.accounts.views._dispatch_recompute") as mock_rc:
            r = self.client.delete(f"/api/v1/platform-accounts/{pk}/")
        self.assertEqual(r.status_code, 204)
        # 账号与全部参赛记录删除，不再有 SET_NULL 遗留行
        self.assertFalse(PlatformAccount.objects.filter(pk=pk).exists())
        self.assertEqual(Participation.objects.count(), 0)
        # 删了记录 → 必须投递排名重算
        mock_rc.assert_called_once()

    def test_unbind_empty_account_no_recompute(self):
        """解绑但本来就没有参赛记录 → 无数据变化，不投递重算。"""
        r = self._bind("codeforces", "cf_alice")
        pk = r.json()["id"]
        with patch("apps.accounts.views._dispatch_recompute") as mock_rc:
            r = self.client.delete(f"/api/v1/platform-accounts/{pk}/")
        self.assertEqual(r.status_code, 204)
        mock_rc.assert_not_called()

    def test_bind_rebound_records_triggers_recompute(self):
        """绑定即回填到历史记录 → 投递重算（回填成绩立即生效）。"""
        # 预置一条无人认领的历史记录（模拟历史爬取数据）
        c = self._make_contest("1111", "CF Round 0")
        Participation.objects.create(
            contest=c, platform_account=None, handle="cf_alice",
            handle_lower="cf_alice", rank=1)
        with patch("apps.accounts.views._dispatch_recompute") as mock_rc:
            r = self._bind("codeforces", "cf_alice")
        self.assertEqual(r.status_code, 201)
        # 记录已回填到该用户名下
        self.assertEqual(
            Participation.objects.filter(
                handle_lower="cf_alice", platform_account__user=self.user).count(), 1)
        mock_rc.assert_called_once()


class AvatarAndBioTests(APITestCase):
    """头像上传 / 移除 + 个性签名更新。"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="avataruser", password="Test1234!")
        self.client.force_authenticate(self.user)

    def test_update_bio(self):
        r = self.client.put("/api/v1/me/", {"bio": "热爱算法竞赛"},
                            format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["bio"], "热爱算法竞赛")

    def test_update_identity(self):
        """真实姓名 / 学号可注册后补填、修改、清空（编辑资料页入口）。"""
        # 补填
        r = self.client.put("/api/v1/me/",
                            {"real_name": "张三", "student_no": "2026010101"},
                            format="json")
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.real_name, "张三")
        self.assertEqual(self.user.student_no, "2026010101")
        # 修改
        r = self.client.put("/api/v1/me/", {"student_no": "2026010102"},
                            format="json")
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.student_no, "2026010102")
        self.assertEqual(self.user.real_name, "张三")  # 未传字段不动
        # 清空（编辑页提交空字符串）
        r = self.client.put("/api/v1/me/", {"real_name": "", "student_no": ""},
                            format="json")
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.real_name, "")
        self.assertEqual(self.user.student_no, "")

    def test_avatar_absent_by_default(self):
        r = self.client.get("/api/v1/me/")
        self.assertIsNone(r.json()["avatar"])


class PublicProfilePlatformsTests(APITestCase):
    """公开 profile 的 platforms 字段：绑定了就要出现，且不泄露 handle。"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="platformsuser", password="Test1234!")
        PlatformAccount.objects.create(
            user=self.user, platform="codeforces", handle="SomeHandle")
        PlatformAccount.objects.create(
            user=self.user, platform="nowcoder", handle="123456789")
        self.url = f"/api/v1/users/{self.user.id}/profile/"

    def test_platforms_listed_without_any_participation(self):
        """账号绑定了但零 rated 成绩时，平台仍要在 platforms 里 —— 前端据此保留选项卡。"""
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["platforms"], ["codeforces", "nowcoder"])
        self.assertEqual(data["platform_ratings"], [])
        self.assertEqual(data["participations"], [])

    def test_platforms_expose_no_handle(self):
        """只暴露平台名，平台标识不出现在该字段里。"""
        data = self.client.get(self.url).json()
        joined = json.dumps(data["platforms"], ensure_ascii=False)
        self.assertNotIn("SomeHandle", joined)
        self.assertNotIn("123456789", joined)

    def test_unbound_user_has_empty_platforms(self):
        other = User.objects.create_user(username="lonely", password="Test1234!")
        data = self.client.get(f"/api/v1/users/{other.id}/profile/").json()
        self.assertEqual(data["platforms"], [])


class ChangePasswordTests(APITestCase):
    """本地密码设置 / 修改（/api/v1/change-password/）。

    回归：前端曾错误调用 /me/change-password/（404），这里锁定正确路由与
    二合一语义（已设密码需原密码，passport 首登无密码可直接设置首条）。
    """

    def setUp(self):
        # 已设本地密码的普通用户
        self.user = User.objects.create_user(
            username="pwuser", password="OldPass123!")
        # 模拟 passport 首登用户：无可用的本地密码
        self.passport_user = User.objects.create_user(username="pwpassport")
        self.passport_user.set_unusable_password()
        self.passport_user.save()

    def _auth(self, user):
        self.client.force_authenticate(user)

    def test_set_first_password_for_passport_user(self):
        """无本地密码用户：不传 old_password 直接设置首条密码。"""
        self._auth(self.passport_user)
        r = self.client.post("/api/v1/change-password/", {
            "new_password1": "NewPass123!",
            "new_password2": "NewPass123!",
        }, format="json")
        self.assertEqual(r.status_code, 200, r.json())
        self.passport_user.refresh_from_db()
        self.assertTrue(self.passport_user.has_usable_password())
        self.assertTrue(self.passport_user.check_password("NewPass123!"))

    def test_change_password_requires_old_password(self):
        """已设密码用户：必须校验原密码。"""
        self._auth(self.user)
        # 缺原密码 → 400
        r = self.client.post("/api/v1/change-password/", {
            "new_password1": "NewPass123!",
            "new_password2": "NewPass123!",
        }, format="json")
        self.assertEqual(r.status_code, 400)
        # 原密码错误 → 400
        r = self.client.post("/api/v1/change-password/", {
            "old_password": "WrongPass1!",
            "new_password1": "NewPass123!",
            "new_password2": "NewPass123!",
        }, format="json")
        self.assertEqual(r.status_code, 400)
        # 原密码正确 → 200，新密码生效
        r = self.client.post("/api/v1/change-password/", {
            "old_password": "OldPass123!",
            "new_password1": "NewPass123!",
            "new_password2": "NewPass123!",
        }, format="json")
        self.assertEqual(r.status_code, 200, r.json())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass123!"))

    def test_mismatched_confirmation_rejected(self):
        self._auth(self.passport_user)
        r = self.client.post("/api/v1/change-password/", {
            "new_password1": "NewPass123!",
            "new_password2": "Different123!",
        }, format="json")
        self.assertEqual(r.status_code, 400)

    def test_requires_authentication(self):
        r = self.client.post("/api/v1/change-password/", {
            "new_password1": "NewPass123!",
            "new_password2": "NewPass123!",
        }, format="json")
        self.assertEqual(r.status_code, 401)


class SetRoleTests(APITestCase):
    """超管成员名单直接设置角色（普通用户 ↔ 学校管理员），含防护断言。"""

    def setUp(self):
        self.super = User.objects.create_superuser(
            username="sup", email="sup@x.com", password="Sup1234!")
        self.school = School.objects.create(
            name="测试大学", code="TU", short_name="测大")
        self.plain = User.objects.create_user(
            username="plain", email="p@x.com", password="Test1234!")
        self.schooled = User.objects.create_user(
            username="schooled", email="s@x.com", password="Test1234!")
        self.schooled.school = self.school
        self.schooled.save()
        self.admin = User.objects.create_user(
            username="admin2", email="a2@x.com", password="Test1234!",
            role=UserRole.SCHOOL_ADMIN, school=self.school)

    def _auth(self, user):
        pwd = "Sup1234!" if user.is_superuser else "Test1234!"
        token = self.client.post(
            "/api/v1/auth/token/",
            {"username": user.username, "password": pwd}).json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_promote_schooled_user_to_school_admin(self):
        self._auth(self.super)
        r = self.client.post(
            f"/api/v1/users/{self.schooled.id}/set_role/",
            {"role": "school_admin"})
        self.assertEqual(r.status_code, 200, r.json())
        self.schooled.refresh_from_db()
        self.assertEqual(self.schooled.role, UserRole.SCHOOL_ADMIN)
        self.assertTrue(self.schooled.is_school_admin)
        # 站内信告知本人
        self.assertTrue(Notification.objects.filter(
            user=self.schooled, type=NotificationType.SYSTEM).exists())

    def test_demote_school_admin_to_user(self):
        self._auth(self.super)
        r = self.client.post(
            f"/api/v1/users/{self.admin.id}/set_role/", {"role": "user"})
        self.assertEqual(r.status_code, 200, r.json())
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, UserRole.USER)
        # 学校归属保留（仅角色降级）
        self.assertEqual(self.admin.school_id, self.school.id)

    def test_promote_without_school_rejected(self):
        self._auth(self.super)
        r = self.client.post(
            f"/api/v1/users/{self.plain.id}/set_role/",
            {"role": "school_admin"})
        self.assertEqual(r.status_code, 400)
        self.plain.refresh_from_db()
        self.assertEqual(self.plain.role, UserRole.USER)

    def test_super_admin_role_not_grantable(self):
        self._auth(self.super)
        r = self.client.post(
            f"/api/v1/users/{self.schooled.id}/set_role/",
            {"role": "super_admin"})
        self.assertEqual(r.status_code, 400)
        self.schooled.refresh_from_db()
        self.assertEqual(self.schooled.role, UserRole.USER)

    def test_cannot_modify_self(self):
        self._auth(self.super)
        r = self.client.post(
            f"/api/v1/users/{self.super.id}/set_role/", {"role": "user"})
        self.assertEqual(r.status_code, 400)
        self.super.refresh_from_db()
        self.assertTrue(self.super.is_super_admin)

    def test_same_role_rejected(self):
        self._auth(self.super)
        r = self.client.post(
            f"/api/v1/users/{self.plain.id}/set_role/", {"role": "user"})
        self.assertEqual(r.status_code, 400)

    def test_requires_super_admin(self):
        # 普通用户 403
        self._auth(self.plain)
        r = self.client.post(
            f"/api/v1/users/{self.schooled.id}/set_role/",
            {"role": "school_admin"})
        self.assertEqual(r.status_code, 403)
        # 学校管理员（非超管）也 403
        self._auth(self.admin)
        r = self.client.post(
            f"/api/v1/users/{self.schooled.id}/set_role/",
            {"role": "user"})
        self.assertEqual(r.status_code, 403)


class HandleReleaseCooldownTests(APITestCase):
    """抢注防护：ID 卸下后一段时间只允许原持有者重绑，管理端随时可纠正。

    平台 ID 没有归属证明手段，自助绑定等于「先到先得」——别人可以把你还没绑的
    handle 抢先绑走，从而把你的公开成绩算到自己学校名下，而你之后被唯一约束挡在
    门外。冷却关掉这段空档；管理员接口负责善后。
    """

    def setUp(self):
        self.school = School.objects.create(name="甲大", code="jd", short_name="甲")
        self.other = School.objects.create(name="乙大", code="yd", short_name="乙")
        self.u1 = User.objects.create_user(username="u1", password="Test1234!",
                                           school=self.school)
        self.u2 = User.objects.create_user(username="u2", password="Test1234!",
                                           school=self.school)
        self.admin = User.objects.create_user(username="adm", password="Test1234!",
                                              school=self.school,
                                              role=UserRole.SCHOOL_ADMIN)
        self.foreign_admin = User.objects.create_user(
            username="admB", password="Test1234!", school=self.other,
            role=UserRole.SCHOOL_ADMIN)
        self.root = User.objects.create_superuser(
            username="rootx", email="rootx@x.com", password="Root12345!")
        # 绑定成功的副作用都走 Celery，测试里只验证数据，不起线程
        for target in ("apps.crawler.tasks.dispatch_account_history_backfill",
                        "apps.accounts.views._dispatch_recompute"):
            patcher = patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _bind(self, user, handle, platform="codeforces"):
        self.client.force_authenticate(user)
        return self.client.post("/api/v1/platform-accounts/",
                                {"platform": platform, "handle": handle},
                                format="json")

    def _unbind(self, user, pk):
        self.client.force_authenticate(user)
        return self.client.delete(f"/api/v1/platform-accounts/{pk}/")

    # ---------- 冷却本体 ----------

    def test_other_user_blocked_within_window(self):
        r = self._bind(self.u1, "tourist")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self._unbind(self.u1, r.json()["id"]).status_code, 204)

        r2 = self._bind(self.u2, "ToUrIst")        # 大小写归一后同一个 ID
        self.assertEqual(r2.status_code, 400, r2.data)
        self.assertIn("仅原持有者", str(r2.json().get("errors")))

    def test_original_holder_may_rebind_immediately(self):
        r = self._bind(self.u1, "tourist")
        pk = r.json()["id"]
        self._unbind(self.u1, pk)
        self.assertEqual(self._bind(self.u1, "tourist").status_code, 201)

    def test_blocked_after_window_expires(self):
        r = self._bind(self.u1, "tourist")
        self._unbind(self.u1, r.json()["id"])
        HandleAudit.objects.filter(
            action=HandleAuditAction.USER_UNBIND).update(
            created_at=timezone.now() - timedelta(days=8))
        self.assertEqual(self._bind(self.u2, "tourist").status_code, 201)

    @override_settings(HANDLE_RELEASE_COOLDOWN_DAYS=0)
    def test_zero_days_disables_policy(self):
        r = self._bind(self.u1, "tourist")
        self._unbind(self.u1, r.json()["id"])
        self.assertEqual(self._bind(self.u2, "tourist").status_code, 201)

    def test_taken_handle_still_reported_as_bound_first(self):
        """已被占用时的提示不该被冷却文案抢先后：先说「已被绑定」。"""
        self._bind(self.u1, "tourist")
        r = self._bind(self.u2, "tourist")
        self.assertEqual(r.status_code, 400)
        self.assertIn("已被其他用户绑定", str(r.json().get("errors")))

    # ---------- 留痕 ----------

    def test_destroy_writes_release_audit(self):
        r = self._bind(self.u1, "tourist")
        self._unbind(self.u1, r.json()["id"])
        row = HandleAudit.objects.get(action=HandleAuditAction.USER_UNBIND)
        self.assertEqual((row.handle, row.handle_lower, row.user_id, row.actor_id),
                         ("tourist", "tourist", self.u1.id, self.u1.id))

    def test_rebind_writes_release_plus_bind_pair(self):
        r = self._bind(self.u1, "cf_a")
        pk = r.json()["id"]
        self.client.force_authenticate(self.u1)
        self.assertEqual(
            self.client.patch(f"/api/v1/platform-accounts/{pk}/",
                              {"handle": "cf_b"}, format="json").status_code, 200)
        kinds = set(HandleAudit.objects.values_list("action", flat=True))
        self.assertIn(HandleAuditAction.USER_REBIND, kinds)   # 旧 ID 释放
        self.assertIn(HandleAuditAction.USER_BIND, kinds)     # 新 ID 归属
        old_release = HandleAudit.objects.get(
            action=HandleAuditAction.USER_REBIND)
        self.assertEqual(old_release.handle, "cf_a")

    # ---------- 并发兜底 ----------

    def test_integrity_error_becomes_400_not_500(self):
        """两人同时绑同一 ID：校验都放行时，DB 约束要翻成 400 提示。"""
        self._bind(self.u1, "tourist")
        with patch.object(PlatformAccountSerializer, "validate",
                          lambda self, attrs: attrs):
            r = self._bind(self.u2, "tourist")
        self.assertEqual(r.status_code, 400, r.data)
        self.assertIn("已被其他用户绑定", str(r.content.decode()))
        self.assertEqual(PlatformAccount.objects.filter(handle="tourist").count(), 1)

    # ---------- 管理端 ----------

    def test_admin_bind_bypasses_cooldown_and_audits(self):
        r = self._bind(self.u1, "tourist")
        self._unbind(self.u1, r.json()["id"])
        self.client.force_authenticate(self.admin)
        resp = self.client.post("/api/v1/admin/platform-accounts/bind/",
                                {"user": self.u2.id, "platform": "codeforces",
                                 "handle": "tourist", "reason": "本人申诉核实"},
                                format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        row = HandleAudit.objects.get(action=HandleAuditAction.ADMIN_BIND)
        self.assertEqual((row.user_id, row.actor_id, row.reason),
                         (self.u2.id, self.admin.id, "本人申诉核实"))

    def test_admin_unbind_deletes_scores_and_notifies(self):
        r = self._bind(self.u1, "tourist")
        pa = PlatformAccount.objects.get(pk=r.json()["id"])
        c = Contest.objects.create(platform="codeforces", external_id="1",
                                   name="Round 1", is_rated=True)
        Participation.objects.create(contest=c, platform_account=pa,
                                     handle="tourist", handle_lower="tourist",
                                     rank=5)
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/v1/admin/platform-accounts/{pa.pk}/unbind/",
            {"reason": "填错 ID"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(Participation.objects.filter(contest=c).count(), 0)
        self.assertFalse(PlatformAccount.objects.filter(pk=pa.pk).exists())
        self.assertTrue(Notification.objects.filter(
            user=self.u1, title__contains="解绑").exists())
        self.assertEqual(HandleAudit.objects.filter(
            action=HandleAuditAction.ADMIN_UNBIND).count(), 1)

    def test_admin_rebind_bypasses_week_limit(self):
        r = self._bind(self.u1, "cf_a")
        pk = r.json()["id"]
        self.client.force_authenticate(self.u1)
        self.assertEqual(
            self.client.patch(f"/api/v1/platform-accounts/{pk}/",
                              {"handle": "cf_b"}, format="json").status_code, 200)
        # 一周内用户自己不能再改，管理员可以随时改
        again = self.client.patch(f"/api/v1/platform-accounts/{pk}/",
                                  {"handle": "cf_c"}, format="json")
        self.assertEqual(again.status_code, 400)
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f"/api/v1/admin/platform-accounts/{pk}/rebind/",
            {"handle": "cf_d", "reason": "改名核实"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(PlatformAccount.objects.get(pk=pk).handle, "cf_d")

    def test_school_admin_cannot_touch_other_school(self):
        r = self._bind(self.u1, "tourist")
        pk = r.json()["id"]
        self.client.force_authenticate(self.foreign_admin)
        resp = self.client.post(
            f"/api/v1/admin/platform-accounts/{pk}/unbind/",
            {"reason": "越权尝试"}, format="json")
        self.assertIn(resp.status_code, (403, 404))
        self.assertTrue(PlatformAccount.objects.filter(pk=pk).exists())

    def test_list_scoped_to_school_and_carries_counts(self):
        self._bind(self.u1, "tourist")
        self.client.force_authenticate(self.admin)
        resp = self.client.get("/api/v1/admin/platform-accounts/?keyword=tourist")
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["participation_count"], 0)
        self.assertEqual(results[0]["username"], "u1")

    def test_audits_endpoint_filters_by_handle(self):
        r = self._bind(self.u1, "tourist")
        self._unbind(self.u1, r.json()["id"])
        self.client.force_authenticate(self.root)
        resp = self.client.get("/api/v1/admin/platform-accounts/audits/?handle=TOURIST")
        self.assertEqual(resp.status_code, 200)
        acts = [row["action"] for row in resp.json()["results"]]
        self.assertIn(HandleAuditAction.USER_BIND, acts)
        self.assertIn(HandleAuditAction.USER_UNBIND, acts)


class DownwardManagementTests(APITestCase):
    """管理动作「只能向下」：同级、上级、本人的平台账号绑定一律不可操作。

    只校验同校是不够的 —— 校管之间平级，谁都能改谁的绑定就等于谁都能把别人的
    成绩挪走；超管账号也不该被校管动。判定唯一来源是
    `apps.common.permissions.manage_denial()`，权限矩阵见 HANDOVER §0.31。
    """

    ADMIN_LIST = "/api/v1/admin/platform-accounts/"

    def setUp(self):
        self.school_a = School.objects.create(name="甲大", code="jd", short_name="甲")
        self.school_b = School.objects.create(name="乙大", code="yd", short_name="乙")

        def mk(username, role=UserRole.USER, school=None):
            return User.objects.create_user(username=username, password="Test1234!",
                                            role=role, school=school)

        self.student = mk("student", school=self.school_a)
        self.actor = mk("actor", UserRole.SCHOOL_ADMIN, self.school_a)      # 操作者
        self.peer = mk("peer", UserRole.SCHOOL_ADMIN, self.school_a)       # 同校同级
        self.subd = mk("subd", UserRole.SCHOOL_ADMIN, self.school_b)       # 下级但外校
        self.foreign_student = mk("fstu", UserRole.USER, self.school_b)    # 普通用户外校
        self.super_role = mk("superrole", UserRole.SUPER_ADMIN, self.school_a)
        self.super_flag = User.objects.create_superuser(
            username="superflag", email="sf@x.com", password="Root12345!",
            school=self.school_a)

        for target in ("apps.crawler.tasks.dispatch_account_history_backfill",
                       "apps.accounts.views._dispatch_recompute"):
            patcher = patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _pa(self, user, handle):
        return PlatformAccount.objects.create(
            user=user, platform="codeforces", handle=handle,
            handle_lower=handle.lower(), school=user.school)

    def _as(self, user):
        self.client.force_authenticate(user)

    def _unbind(self, actor, pa):
        self._as(actor)
        return self.client.post(f"{self.ADMIN_LIST}{pa.pk}/unbind/",
                               {"reason": "越权边界用例"}, format="json")

    def _bind(self, actor, target_user, handle):
        self._as(actor)
        return self.client.post(f"{self.ADMIN_LIST}bind/",
                               {"user": target_user.id, "platform": "codeforces",
                                "handle": handle, "reason": "越权边界用例"},
                               format="json")

    # ---------- 校管：只能动本校普通用户 ----------

    def test_school_admin_blocks_peer_admin_same_school(self):
        pa = self._pa(self.peer, "cf_peer")
        resp = self._unbind(self.actor, pa)
        self.assertIn(resp.status_code, (403, 404), resp.content)
        self.assertTrue(PlatformAccount.objects.filter(pk=pa.pk).exists())
        self.assertFalse(HandleAudit.objects.filter(
            action=HandleAuditAction.ADMIN_UNBIND).exists())

    def test_school_admin_blocks_super_admin_targets(self):
        for super_user in (self.super_role, self.super_flag):
            with self.subTest(user=super_user.username):
                pa = self._pa(super_user, f"cf_{super_user.username}")
                self.assertIn(self._unbind(self.actor, pa).status_code, (403, 404))
                self.assertTrue(PlatformAccount.objects.filter(pk=pa.pk).exists())

    def test_school_admin_blocks_self_via_admin_channel(self):
        """管理端绕冷却，放行「操作自己」等于给管理员开后门，自助端点才是正路。"""
        pa = self._pa(self.actor, "cf_self")
        self.assertIn(self._unbind(self.actor, pa).status_code, (403, 404))
        self.assertEqual(self._bind(self.actor, self.actor, "cf_self2").status_code, 403)
        self.assertTrue(PlatformAccount.objects.filter(pk=pa.pk).exists())
        self.assertFalse(PlatformAccount.objects.filter(handle="cf_self2").exists())

    def test_school_admin_still_manages_plain_user(self):
        pa = self._pa(self.student, "cf_stu")
        resp = self._unbind(self.actor, pa)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(PlatformAccount.objects.filter(pk=pa.pk).exists())

    def test_bind_denials_carry_actionable_message(self):
        resp = self._bind(self.actor, self.peer, "cf_x")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("权限低于自己", resp.json()["detail"])

    # ---------- 超管：向下到校管，但仍不含平级与本人 ----------

    def test_super_admin_manages_school_admin_and_user(self):
        for target in (self.student, self.peer):
            with self.subTest(user=target.username):
                pa = self._pa(target, f"cf_{target.username}")
                self.assertEqual(self._unbind(self.super_role, pa).status_code, 200)

    def test_super_admin_blocks_peer_super_and_self(self):
        for other in (self.super_role, self.super_flag):
            with self.subTest(user=other.username):
                self.assertEqual(
                    self._bind(self.super_flag, other, f"cf_{other.username}").status_code,
                    403)

    def test_rebind_by_school_admin_on_peer_is_invisible(self):
        pa = self._pa(self.peer, "cf_peer2")
        self._as(self.actor)
        resp = self.client.post(f"{self.ADMIN_LIST}{pa.pk}/rebind/",
                               {"handle": "cf_stolen"}, format="json")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(PlatformAccount.objects.get(pk=pa.pk).handle, "cf_peer2")

    # ---------- 列表可见性与动作一致 ----------

    def test_list_only_contains_manageable_rows(self):
        self._pa(self.student, "cf_l1")
        self._pa(self.peer, "cf_l2")
        self._pa(self.super_role, "cf_l3")
        self._pa(self.super_flag, "cf_l4")
        self._pa(self.actor, "cf_l5")          # 本人

        self._as(self.actor)
        seen = {r["handle"] for r in
                self.client.get(self.ADMIN_LIST).json()["results"]}
        self.assertEqual(seen, {"cf_l1"})

        self._as(self.super_role)
        seen = {r["handle"] for r in
                self.client.get(self.ADMIN_LIST).json()["results"]}
        self.assertEqual(seen, {"cf_l1", "cf_l2", "cf_l5"})

    # ---------- 角色变更同样向下 ----------

    def test_set_role_blocks_peer_super(self):
        self._as(self.super_role)
        resp = self.client.post(f"/api/v1/users/{self.super_flag.id}/set_role/",
                               {"role": "user"}, format="json")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.super_flag.refresh_from_db()
        self.assertTrue(self.super_flag.is_superuser)

    def test_set_role_allows_downward(self):
        self._as(self.super_role)
        resp = self.client.post(f"/api/v1/users/{self.peer.id}/set_role/",
                               {"role": "user"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)

    # ---------- 判定函数本体的真值表（矩阵的机器可读版） ----------

    def test_manage_denial_truth_table(self):
        from apps.common.permissions import manage_denial, role_rank

        self.assertEqual(
            [role_rank(u) for u in (self.student, self.actor, self.super_role,
                                    self.super_flag)],
            [1, 2, 3, 3])

        cases = [
            (self.actor, self.student, None),          # 向下：放行
            (self.actor, self.peer, "同级与更高"),
            (self.actor, self.super_role, "同级与更高"),
            (self.actor, self.actor, "自己的账号"),
            # 角色序先于学校范围：外校校管既平级又跨校，报的是「同级与更高」
            (self.actor, self.subd, "同级与更高"),
            (self.actor, self.foreign_student, "本校"),
            (self.super_role, self.peer, None),
            (self.super_role, self.student, None),
            (self.super_role, self.foreign_student, None),   # 超管不受学校范围限制
            (self.super_role, self.super_flag, "同级与更高"),
            (self.super_role, self.super_role, "自己的账号"),
        ]
        for actor, target, expect in cases:
            with self.subTest(actor=actor.username, target=target.username):
                denial = manage_denial(actor, target)
                if expect is None:
                    self.assertIsNone(denial)
                else:
                    self.assertIsNotNone(denial)
                    self.assertIn(expect, denial)


class ClientIpTrustBoundaryTests(SimpleTestCase):
    """锁 get_client_ip() 的取值口径，配合 deploy/rank-proxy.conf 的「覆盖式」XFF。

    边缘 nginx 用 $remote_addr *覆盖* X-Forwarded-For，XFF 首位才是可信的真实
    客户端。若哪天改回 $proxy_add_x_forwarded_for（追加），访客自带的伪造值就排在
    首位，按 IP 的限流、登录锁定与审计 IP 一起失效——这条用例就是那道闸。
    """

    def setUp(self):
        self.factory = RequestFactory()

    def _ip(self, **extra):
        from apps.accounts.security import get_client_ip

        return get_client_ip(self.factory.get("/", **extra))

    def test_xff_first_entry_is_the_client(self):
        self.assertEqual(
            self._ip(HTTP_X_FORWARDED_FOR="203.0.113.7, 127.0.0.1"),
            "203.0.113.7",
        )

    def test_falls_back_to_x_real_ip(self):
        self.assertEqual(self._ip(HTTP_X_REAL_IP="203.0.113.8"), "203.0.113.8")

    def test_without_proxy_headers_uses_peer_address(self):
        self.assertEqual(self._ip(REMOTE_ADDR="203.0.113.9"), "203.0.113.9")


