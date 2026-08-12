from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

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
