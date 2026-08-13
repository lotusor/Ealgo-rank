"""#3 管理员申请与审批流单元测试。"""
from rest_framework.test import APITestCase

from apps.accounts.models import (
    Notification,
    NotificationType,
    PlatformAccount,
    User,
    UserRole,
)
from apps.common.models import Platform
from apps.schools.models import (
    AdminApplicationStatus,
    School,
    SchoolAdminApplication,
    ScoreConfig,
)

BASE = "/api/v1"
LIST = f"{BASE}/applications/"
DETAIL = lambda pk: f"{BASE}/applications/{pk}/"
APPROVE = lambda pk: f"{BASE}/applications/{pk}/approve/"
REJECT = lambda pk: f"{BASE}/applications/{pk}/reject/"
CANCEL = lambda pk: f"{BASE}/applications/{pk}/cancel/"


def make_user(username, role=UserRole.USER, school=None, password="Test1234!"):
    return User.objects.create_user(
        username=username, password=password, role=role, school=school)


class SchoolAdminApplicationFlowTests(APITestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="测试大学", code="testu", short_name="测试")
        self.applicant = make_user("applicant", school=None)
        self.other = make_user("other")
        self.super = make_user("super", role=UserRole.SUPER_ADMIN)
        # applicant 名下有一个平台账号，初始无学校
        PlatformAccount.objects.create(
            user=self.applicant, platform=Platform.CODEFORCES,
            handle="cf_app", handle_lower="cf_app")

    # ---------- 提交 ----------
    def test_submit_creates_pending_and_notifies_super(self):
        self.client.force_authenticate(self.applicant)
        resp = self.client.post(LIST, {
            "school": self.school.id,
            "reason": "我是该校教练",
            "contact": "a@b.com",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["status"], AdminApplicationStatus.PENDING)
        self.assertEqual(SchoolAdminApplication.objects.count(), 1)
        # 站内信通知超管
        self.assertTrue(Notification.objects.filter(
            user=self.super,
            type=NotificationType.APPLICATION_RECEIVED).exists())

    def test_duplicate_pending_rejected(self):
        SchoolAdminApplication.objects.create(
            applicant=self.applicant, school=self.school,
            reason="x", status=AdminApplicationStatus.PENDING)
        self.client.force_authenticate(self.applicant)
        resp = self.client.post(LIST, {
            "school": self.school.id, "reason": "again"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_submit_requires_existing_school(self):
        self.client.force_authenticate(self.applicant)
        resp = self.client.post(LIST, {
            "school": 99999, "reason": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)

    # ---------- 审批通过 ----------
    def test_approve_updates_role_school_and_syncs_accounts(self):
        app = SchoolAdminApplication.objects.create(
            applicant=self.applicant, school=self.school, reason="x")
        self.client.force_authenticate(self.super)
        resp = self.client.post(APPROVE(app.id))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.role, UserRole.SCHOOL_ADMIN)
        self.assertEqual(self.applicant.school_id, self.school.id)
        self.assertIsNotNone(self.applicant.school_bound_at)
        # 平台账号同步到该校
        pa = PlatformAccount.objects.get(user=self.applicant)
        self.assertEqual(pa.school_id, self.school.id)
        # 站内信通知申请人
        self.assertTrue(Notification.objects.filter(
            user=self.applicant,
            type=NotificationType.APPLICATION_REVIEWED).exists())

    def test_non_super_cannot_approve(self):
        app = SchoolAdminApplication.objects.create(
            applicant=self.applicant, school=self.school, reason="x")
        self.client.force_authenticate(self.other)
        resp = self.client.post(APPROVE(app.id))
        self.assertEqual(resp.status_code, 403)

    def test_approve_only_pending(self):
        app = SchoolAdminApplication.objects.create(
            applicant=self.applicant, school=self.school, reason="x",
            status=AdminApplicationStatus.APPROVED)
        self.client.force_authenticate(self.super)
        resp = self.client.post(APPROVE(app.id))
        self.assertEqual(resp.status_code, 400)

    # ---------- 驳回 ----------
    def test_reject_sets_status_and_notifies(self):
        app = SchoolAdminApplication.objects.create(
            applicant=self.applicant, school=self.school, reason="x")
        self.client.force_authenticate(self.super)
        resp = self.client.post(REJECT(app.id),
                                {"review_comment": "材料不足"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        app.refresh_from_db()
        self.assertEqual(app.status, AdminApplicationStatus.REJECTED)
        self.assertEqual(app.review_comment, "材料不足")
        self.assertTrue(Notification.objects.filter(
            user=self.applicant,
            type=NotificationType.APPLICATION_REVIEWED).exists())

    # ---------- 撤回 ----------
    def test_cancel_own_pending(self):
        app = SchoolAdminApplication.objects.create(
            applicant=self.applicant, school=self.school, reason="x",
            status=AdminApplicationStatus.PENDING)
        self.client.force_authenticate(self.applicant)
        resp = self.client.post(CANCEL(app.id))
        self.assertEqual(resp.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, AdminApplicationStatus.CANCELLED)

    def test_cancel_other_forbidden(self):
        app = SchoolAdminApplication.objects.create(
            applicant=self.applicant, school=self.school, reason="x",
            status=AdminApplicationStatus.PENDING)
        self.client.force_authenticate(self.other)
        # 非申请人看不到该申请（get_queryset 已隐藏），返回 404 而非 403
        resp = self.client.post(CANCEL(app.id))
        self.assertEqual(resp.status_code, 404)

    # ---------- 列表可见范围 + 筛选 ----------
    def test_list_visibility_applicant_sees_only_own(self):
        SchoolAdminApplication.objects.create(
            applicant=self.applicant, school=self.school, reason="mine")
        SchoolAdminApplication.objects.create(
            applicant=self.other, school=self.school, reason="others")
        self.client.force_authenticate(self.applicant)
        resp = self.client.get(LIST)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["reason"], "mine")

    def test_list_super_sees_all(self):
        SchoolAdminApplication.objects.create(
            applicant=self.applicant, school=self.school, reason="a")
        SchoolAdminApplication.objects.create(
            applicant=self.other, school=self.school, reason="b")
        self.client.force_authenticate(self.super)
        resp = self.client.get(LIST)
        self.assertEqual(resp.data["count"], 2)

    def test_list_status_filter(self):
        SchoolAdminApplication.objects.create(
            applicant=self.applicant, school=self.school, reason="p",
            status=AdminApplicationStatus.PENDING)
        SchoolAdminApplication.objects.create(
            applicant=self.other, school=self.school, reason="r",
            status=AdminApplicationStatus.REJECTED)
        self.client.force_authenticate(self.super)
        resp = self.client.get(LIST, {"status": "rejected"})
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["reason"], "r")

    def test_list_keyword_filter(self):
        SchoolAdminApplication.objects.create(
            applicant=self.applicant, school=self.school,
            reason="我是教练", contact="coach@x.com")
        SchoolAdminApplication.objects.create(
            applicant=self.other, school=self.school, reason="别的")
        self.client.force_authenticate(self.super)
        resp = self.client.get(LIST, {"keyword": "教练"})
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["reason"], "我是教练")

    def test_pagination_shape(self):
        # 用非 pending 状态避免 (applicant, school) 待审唯一约束；超管列表仍可见
        for i in range(25):
            SchoolAdminApplication.objects.create(
                applicant=self.applicant, school=self.school,
                reason=f"r{i}", status=AdminApplicationStatus.REJECTED)
        self.client.force_authenticate(self.super)
        resp = self.client.get(LIST, {"page_size": 10})
        self.assertIn("count", resp.data)
        self.assertIn("page", resp.data)
        self.assertIn("total_pages", resp.data)
        self.assertIn("results", resp.data)
        self.assertEqual(len(resp.data["results"]), 10)


BASE = "/api/v1"
SC_LIST = f"{BASE}/score-configs/"
SC_DETAIL = lambda pk: f"{BASE}/score-configs/{pk}/"


class ScoreConfigPermissionTests(APITestCase):
    """#5 权限：积分系数为全局单例，仅超级管理员可读写；校管一律 403。"""

    def setUp(self):
        self.school_a = School.objects.create(
            name="A大学", code="a", short_name="A")
        self.admin_a = make_user("adminA", role=UserRole.SCHOOL_ADMIN,
                                 school=self.school_a)
        self.super = make_user("super", role=UserRole.SUPER_ADMIN)
        # 全局唯一配置
        ScoreConfig.objects.create(cf_factor=1.1)

    def test_admin_read_forbidden(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.get(SC_LIST)
        self.assertEqual(resp.status_code, 403)

    def test_admin_write_forbidden(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.patch(SC_DETAIL(1), {"cf_factor": "9.9"},
                                 format="json")
        self.assertEqual(resp.status_code, 403)

    def test_admin_create_forbidden(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.post(SC_LIST, {"cf_factor": "1.5"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_super_can_read_and_update(self):
        self.client.force_authenticate(self.super)
        resp = self.client.get(SC_LIST)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        cfg_id = resp.data["results"][0]["id"]
        resp2 = self.client.patch(SC_DETAIL(cfg_id), {"cf_factor": "2.5"},
                                  format="json")
        self.assertEqual(resp2.status_code, 200, resp2.content)
        self.assertEqual(float(ScoreConfig.objects.get(id=cfg_id).cf_factor), 2.5)
