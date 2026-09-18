"""#4 校管参赛记录隔离：仅可见/可操作本校记录，跨校请求 404。

另含阶段2（2026-09-18）新增的 Contest 只读接口测试：状态派生、系列、
关键字、结束时间区间、排序白名单与 /contests/meta/ 元数据。
"""
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
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


class ContestApiTests(APITestCase):
    """竞赛日历 / 比赛列表所需的 Contest 只读接口（阶段 2）。

    覆盖：匿名可读、状态派生过滤、系列 / 关键字 / 结束时间区间、
    排序白名单，以及 /contests/meta/ 元数据；并锁定「不带参数时默认行为
    不变」这条回归底线（既有比赛列表页依赖它）。
    """

    LIST = f"{BASE}/contests/"
    META = f"{BASE}/contests/meta/"

    def setUp(self):
        # 清空 DRF 限流计数：本类用例较多，且全量套件里其他 anon 请求也会累加
        # （anon 60/min），不清会误触 429 让用例变得依赖执行顺序。
        cache.clear()
        now = timezone.now()
        self.finished = Contest.objects.create(
            platform=Platform.CODEFORCES, external_id="fin", name="已结束赛",
            series="Div. 2", is_rated=True,
            start_time=now - timedelta(hours=3),
            end_time=now - timedelta(hours=1),
        )
        self.ongoing = Contest.objects.create(
            platform=Platform.ATCODER, external_id="ong", name="进行中赛",
            series="ABC", is_rated=True,
            start_time=now - timedelta(minutes=30),
            end_time=now + timedelta(minutes=90),
        )
        self.upcoming = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="upc", name="未来赛",
            series="牛客周赛", is_rated=False,
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=2),
        )

    @staticmethod
    def _ids(resp):
        return {row["id"] for row in resp.data["results"]}

    def tearDown(self):
        # 不把自己的限流计数留给后续用例，保证套件整体顺序无关
        cache.clear()

    # ---- 基础可读性 ----

    def test_anonymous_can_list(self):
        """日历是公开页面，列表接口必须匿名可读。"""
        resp = self.client.get(self.LIST)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 3)

    def test_default_behaviour_unchanged(self):
        """不带参数时默认返回全部、按 -start_time 排序（回归底线）。"""
        resp = self.client.get(self.LIST)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 3)
        starts = [row["start_time"] for row in resp.data["results"]]
        self.assertEqual(starts, sorted(starts, reverse=True))

    # ---- 状态派生过滤 ----

    def test_status_finished(self):
        resp = self.client.get(self.LIST, {"status": "finished"})
        self.assertEqual(self._ids(resp), {self.finished.id})

    def test_status_ongoing(self):
        resp = self.client.get(self.LIST, {"status": "ongoing"})
        self.assertEqual(self._ids(resp), {self.ongoing.id})

    def test_status_upcoming(self):
        resp = self.client.get(self.LIST, {"status": "upcoming"})
        self.assertEqual(self._ids(resp), {self.upcoming.id})

    def test_unknown_status_is_ignored(self):
        """无法识别的 status 不报错、也不过滤（避免前端拼错参数就查不到数据）。"""
        resp = self.client.get(self.LIST, {"status": "whatever"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 3)

    # ---- 其他筛选维度 ----

    def test_series_filter(self):
        resp = self.client.get(self.LIST, {"series": "ABC"})
        self.assertEqual(self._ids(resp), {self.ongoing.id})

    def test_search_matches_name_and_series(self):
        resp = self.client.get(self.LIST, {"search": "未来"})
        self.assertEqual(self._ids(resp), {self.upcoming.id})
        resp = self.client.get(self.LIST, {"search": "Div. 2"})
        self.assertEqual(self._ids(resp), {self.finished.id})

    def test_end_time_range(self):
        """日历按月取场次：按 end_time 区间过滤。

        取「从现在起 1 天后 ~ 3 天后」的窗口，应只命中 2 天后结束的未来赛，
        排除已结束（now-1h）与进行中（now+90min）两场。
        """
        now = timezone.now()
        after = (now + timedelta(days=1)).isoformat()
        before = (now + timedelta(days=3)).isoformat()
        resp = self.client.get(self.LIST, {"end_after": after, "end_before": before})
        self.assertEqual(self._ids(resp), {self.upcoming.id})

    def test_ordering_whitelist_ascending(self):
        resp = self.client.get(self.LIST, {"ordering": "start_time"})
        self.assertEqual(
            [row["id"] for row in resp.data["results"]],
            [self.finished.id, self.ongoing.id, self.upcoming.id],
        )

    def test_ordering_rejects_non_whitelisted_field(self):
        """排序白名单外的字段不生效，回落到默认排序，不抛 500。"""
        resp = self.client.get(self.LIST, {"ordering": "raw_meta"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 3)

    # ---- 元数据 ----

    def test_meta_anonymous_and_counts(self):
        resp = self.client.get(self.META)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 3)
        self.assertEqual(resp.data["finished"], 1)
        self.assertEqual(resp.data["ongoing"], 1)
        self.assertEqual(resp.data["upcoming"], 1)
        self.assertEqual(resp.data["rated"], 2)

    def test_meta_platforms_and_series(self):
        resp = self.client.get(self.META)
        self.assertEqual(resp.status_code, 200)
        platform_keys = {p["key"] for p in resp.data["platforms"]}
        self.assertEqual(
            platform_keys,
            {Platform.CODEFORCES, Platform.ATCODER, Platform.NOWCODER},
        )
        counts = {p["key"]: p["count"] for p in resp.data["platforms"]}
        self.assertEqual(counts[Platform.CODEFORCES], 1)
        self.assertEqual(set(resp.data["series"]), {"Div. 2", "ABC", "牛客周赛"})
        self.assertIn("latest_sync_at", resp.data)
