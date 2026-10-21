"""登录安全测试：失败锁定、限流（NAT 友好）、登出吊销、异常检测。

阈值用 override_settings 调小，保证测试确定且快速。
"""
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuthLog, AuthEventType, User
from apps.accounts.security import (
    detect_login_logout_oscillation,
    get_security_config,
)

SEC = {
    "AUTH_MAX_CONSECUTIVE_FAILURES": 3,
    "AUTH_LOCK_MINUTES": 15,
    "AUTH_FAILURE_WINDOW_MINUTES": 15,
    "AUTH_MAX_FAILURES_PER_WINDOW": 4,
    "AUTH_DEVICE_LOGIN_MAX": 3,
    "AUTH_DEVICE_WINDOW_MINUTES": 10,
    "AUTH_IP_LOGIN_MAX": 300,
    "AUTH_IP_LOGIN_WINDOW_MINUTES": 10,
    "AUTH_LOGOUT_USER_MAX": 5,
    "AUTH_LOGOUT_USER_WINDOW_MINUTES": 10,
    "AUTH_LOGOUT_SESSION_MAX": 3,
    "AUTH_ANOMALY_DISTINCT_IDS": 3,
    "AUTH_ANOMALY_TOGGLE_PAIRS": 3,
}


def _make_user(username, password="Passw0rd!"):
    u = User.objects.create_user(username=username, password=password,
                                 email=f"{username}@example.com")
    return u


@override_settings(**SEC)
class LoginLockoutTests(TestCase):
    def setUp(self):
        self.user = _make_user("alice")

    def _fail(self, username="alice", password="wrong", **extra):
        return self.client.post(
            "/api/v1/auth/token/",
            {"username": username, "password": password}, **extra)

    def _ok(self, **extra):
        return self.client.post(
            "/api/v1/auth/token/",
            {"username": "alice", "password": "Passw0rd!"}, **extra)

    def test_consecutive_failures_lock_account(self):
        for _ in range(SEC["AUTH_MAX_CONSECUTIVE_FAILURES"]):
            self._fail()
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_locked)
        # 锁定后继续尝试 → 423
        resp = self._fail()
        self.assertEqual(resp.status_code, 423)
        self.assertEqual(resp.data["code"], "account_locked")
        self.assertIn("Retry-After", resp)

    def test_success_resets_counter(self):
        self._fail()
        self._fail()
        resp = self._ok()
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_count, 0)
        self.assertFalse(self.user.is_locked)

    def test_locked_account_rejects_valid_password(self):
        for _ in range(SEC["AUTH_MAX_CONSECUTIVE_FAILURES"]):
            self._fail()
        resp = self._ok()
        self.assertEqual(resp.status_code, 423)

    @override_settings(AUTH_DEVICE_LOGIN_MAX=100)
    def test_admin_unlock_allows_login(self):
        for _ in range(SEC["AUTH_MAX_CONSECUTIVE_FAILURES"]):
            self._fail()
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_locked)
        self.user.unlock(rotate_stamp=False)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_locked)
        self.assertEqual(self._ok().status_code, 200)

    def test_lock_auto_expires(self):
        self.user.locked_until = timezone.now() - timezone.timedelta(minutes=1)
        self.user.save()
        self.assertFalse(self.user.is_locked)
        self.assertEqual(self._ok().status_code, 200)


@override_settings(**SEC)
class NatFriendlyThrottlingTests(TestCase):
    """校园网共享 NAT 出口：同 IP 不同设备互不影响；IP 阈值放宽。"""

    SHARED_IP = "203.0.113.50"

    def test_device_isolation_behind_same_ip(self):
        # 攻击者设备（同一校园网出口 IP）反复失败
        dev_attacker = {"HTTP_X_FORWARDED_FOR": self.SHARED_IP,
                        "HTTP_X_DEVICE_ID": "attacker-device"}
        for _ in range(SEC["AUTH_DEVICE_LOGIN_MAX"]):
            self._fail_ghost("ghost", **dev_attacker)
        # 攻击者设备第 4 次被拦（device_rate）
        r = self._fail_ghost("ghost", **dev_attacker)
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.data["code"], "device_rate")

        # 受害者设备（同一 IP，不同设备指纹）用正确密码登录 → 成功，不被误伤
        victim = _make_user("bob")
        r = self.client.post("/api/v1/auth/token/",
                             {"username": "bob", "password": "Passw0rd!"},
                             HTTP_X_FORWARDED_FOR=self.SHARED_IP,
                             HTTP_X_DEVICE_ID="victim-device")
        self.assertEqual(r.status_code, 200)

    def test_ip_threshold_generous_vs_device(self):
        cfg = get_security_config()
        self.assertGreater(cfg["IP_LOGIN_MAX"], cfg["DEVICE_LOGIN_MAX"] * 5)

    @override_settings(AUTH_DEVICE_LOGIN_MAX=100)
    def test_unknown_username_rate_limited_by_identifier(self):
        for _ in range(SEC["AUTH_MAX_FAILURES_PER_WINDOW"]):
            self._fail_ghost("ghost-x")
        r = self._fail_ghost("ghost-x")
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.data["code"], "identifier_rate")

    @override_settings(AUTH_DEVICE_LOGIN_MAX=100, AUTH_ANOMALY_DISTINCT_IDS=3)
    def test_credential_stuffing_blocked(self):
        dev = {"HTTP_X_DEVICE_ID": "stuffing-device"}
        for i in range(SEC["AUTH_ANOMALY_DISTINCT_IDS"]):
            self._fail_ghost(f"victim{i}", **dev)
        r = self._fail_ghost("victimX", **dev)
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.data["code"], "credential_stuffing")

    def _fail_ghost(self, name, **extra):
        return self.client.post(
            "/api/v1/auth/token/",
            {"username": name, "password": "wrong"}, **extra)


@override_settings(**SEC)
class LogoutAndRevocationTests(TestCase):
    def setUp(self):
        self.user = _make_user("carol")

    def _login(self):
        return self.client.post(
            "/api/v1/auth/token/",
            {"username": "carol", "password": "Passw0rd!"}).data

    def test_logout_blacklists_refresh(self):
        tokens = self._login()
        # 带令牌登出
        r = self.client.post("/api/v1/auth/logout/",
                             {"refresh": tokens["refresh"]},
                             HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(r.status_code, 200)
        # 被吊销的 refresh 不能再换发
        r2 = self.client.post("/api/v1/auth/token/refresh/",
                             {"refresh": tokens["refresh"]})
        self.assertEqual(r2.status_code, 401)

    def test_logout_all_rotates_stamp_and_revokes_access(self):
        tokens = self._login()
        # 登出全部设备 → 轮换安全戳
        r = self.client.post("/api/v1/auth/logout/",
                             {"refresh": tokens["refresh"], "all": True},
                             HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(r.status_code, 200)
        # 旧 access 令牌立即失效
        me = self.client.get("/api/v1/me/",
                             HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(me.status_code, 401)

    @override_settings(AUTH_LOGOUT_SESSION_MAX=100)
    def test_logout_rate_limited_per_user(self):
        tokens = self._login()
        # 超过用户维度上限 → 429
        for _ in range(SEC["AUTH_LOGOUT_USER_MAX"]):
            self.client.post("/api/v1/auth/logout/",
                             {"refresh": tokens["refresh"]},
                             HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        r = self.client.post("/api/v1/auth/logout/",
                             {"refresh": tokens["refresh"]},
                             HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.data["code"], "logout_user_rate")

    def test_stamp_rotation_revokes_old_token(self):
        tokens = self._login()
        old_access = tokens["access"]
        # 改密式轮换安全戳（与解锁/登出全部同机制）
        self.user.refresh_from_db()
        self.user.rotate_security_stamp()
        me = self.client.get("/api/v1/me/",
                             HTTP_AUTHORIZATION=f"Bearer {old_access}")
        self.assertEqual(me.status_code, 401)


@override_settings(**SEC)
class AnomalyDetectionTests(TestCase):
    def setUp(self):
        self.user = _make_user("dave")

    def test_login_logout_oscillation_detected(self):
        now = timezone.now()
        for i in range(4):
            AuthLog.objects.create(
                user=self.user, event_type=AuthEventType.LOGIN_SUCCESS,
                identifier="dave", created_at=now)
            AuthLog.objects.create(
                user=self.user, event_type=AuthEventType.LOGOUT,
                identifier="dave", created_at=now)
        self.assertTrue(detect_login_logout_oscillation(self.user))
        self.assertTrue(
            AuthLog.objects.filter(user=self.user,
                                   event_type=AuthEventType.ANOMALY).exists())
