"""#4 校管参赛记录隔离：仅可见/可操作本校记录，跨校请求 404。"""
from rest_framework.test import APITestCase

from apps.accounts.models import PlatformAccount, User, UserRole
from apps.common.models import Platform
from apps.contests.models import Contest, Participation
from apps.schools.models import School

BASE = "/api/v1"
PART_LIST = f"{BASE}/participations/"
PART_EXCLUDE = lambda pk: f"{BASE}/participations/{pk}/exclude/"
PART_RESTORE = lambda pk: f"{BASE}/participations/{pk}/restore/"


def make_user(username, role=UserRole.USER, school=None):
    return User.objects.create_user(
        username=username, password="Test1234!", role=role, school=school)


class ParticipationIsolationTests(APITestCase):
    def setUp(self):
        self.school_a = School.objects.create(
            name="A大学", code="a", short_name="A")
        self.school_b = School.objects.create(
            name="B大学", code="b", short_name="B")
        self.admin_a = make_user("adminA", UserRole.SCHOOL_ADMIN,
                                 school=self.school_a)
        self.admin_b = make_user("adminB", UserRole.SCHOOL_ADMIN,
                                 school=self.school_b)

        self.pa_a = PlatformAccount.objects.create(
            user=make_user("uA"), platform=Platform.CODEFORCES,
            handle="cf_a", school=self.school_a)
        self.pa_b = PlatformAccount.objects.create(
            user=make_user("uB"), platform=Platform.CODEFORCES,
            handle="cf_b", school=self.school_b)

        self.contest = Contest.objects.create(
            platform=Platform.CODEFORCES, external_id="c1",
            name="测试赛", is_rated=True)
        self.part_a = Participation.objects.create(
            contest=self.contest, platform_account=self.pa_a, handle="cf_a")
        self.part_b = Participation.objects.create(
            contest=self.contest, platform_account=self.pa_b, handle="cf_b")

    def test_admin_sees_only_own_school(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.get(PART_LIST)
        self.assertEqual(resp.status_code, 200)
        ids = {p["id"] for p in resp.data["results"]}
        self.assertIn(self.part_a.id, ids)
        self.assertNotIn(self.part_b.id, ids)

    def test_admin_cannot_exclude_other_school(self):
        self.client.force_authenticate(self.admin_a)
        # 跨校记录不在 queryset 内 → get_object 返回 404
        resp = self.client.post(PART_EXCLUDE(self.part_b.id))
        self.assertEqual(resp.status_code, 404)
        self.part_b.refresh_from_db()
        self.assertFalse(self.part_b.is_excluded)

    def test_admin_can_exclude_own_school(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.post(PART_EXCLUDE(self.part_a.id))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.part_a.refresh_from_db()
        self.assertTrue(self.part_a.is_excluded)

    def test_other_school_admin_sees_only_their_own(self):
        self.client.force_authenticate(self.admin_b)
        resp = self.client.get(PART_LIST)
        ids = {p["id"] for p in resp.data["results"]}
        self.assertIn(self.part_b.id, ids)
        self.assertNotIn(self.part_a.id, ids)
