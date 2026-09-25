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
            {p.value for p in Platform},
            "meta 的平台清单必须与注册表同步：漏一项前端筛选就少一个平台")
        counts = {p["key"]: p["count"] for p in resp.data["platforms"]}
        self.assertEqual(counts[Platform.CODEFORCES], 1)
        # 只做日历展示的平台（洛谷）也在清单里，0 场次也要给出来，
        # 否则前端 chip 会随同步状态闪进闪出
        self.assertEqual(counts[Platform.LUOGU], 0)
        flags = {p["key"]: p for p in resp.data["platforms"]}
        self.assertTrue(flags[Platform.CODEFORCES]["scoring"])
        self.assertTrue(flags[Platform.CODEFORCES]["bindable"])
        self.assertFalse(flags[Platform.LUOGU]["scoring"])
        self.assertFalse(flags[Platform.LUOGU]["bindable"])
        self.assertTrue(flags[Platform.LUOGU]["calendar"])
        self.assertEqual(set(resp.data["series"]), {"Div. 2", "ABC", "牛客周赛"})
        self.assertIn("latest_sync_at", resp.data)


class ProfileOnlyContestVisibilityTests(APITestCase):
    """主页派生的「不计分锚点赛次」不得出现在公共比赛列表。

    它们存在的唯一理由是让个人主页参赛记录能显示校内赛/同步赛（C 阶段）；
    「比赛列表」与「难度系数设置页」都走这个接口，混进来就是脏数据。
    """

    LIST = f"{BASE}/contests/"

    def setUp(self):
        cache.clear()
        now = timezone.now()
        self.real = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="real", name="真比赛",
            is_rated=True, start_time=now - timedelta(days=3),
            end_time=now - timedelta(days=3) + timedelta(hours=2))
        self.anchor = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="anchor", name="校内选拔赛",
            is_rated=False, start_time=now - timedelta(days=30),
            end_time=now - timedelta(days=30) + timedelta(hours=2),
            rated_source="profile-joined-history",
            raw_meta={"source": "profile_joined"})

    def tearDown(self):
        cache.clear()

    def _ids(self, **qp):
        resp = self.client.get(self.LIST, qp)
        return {r["id"] for r in resp.data["results"]}

    def test_default_list_hides_anchor(self):
        self.assertEqual(self._ids(), {self.real.pk})

    def test_derived_filters_also_hide_anchor(self):
        self.assertEqual(self._ids(status="finished"), {self.real.pk})
        # 锚点赛次本身就是 is_rated=False，但按 rated 筛也拿不到它：
        # 它不是「一场未判 rated 的真实比赛」，而是只为展示而存在的派生行
        self.assertEqual(self._ids(is_rated="false"), set())

    def test_include_profile_only_brings_it_back(self):
        self.assertEqual(self._ids(include_profile_only="1"),
                         {self.real.pk, self.anchor.pk})


class CalendarRowVisibilityTests(APITestCase):
    """日历排期行（未开赛的官方排期）的可见性口径。

    「比赛列表」是历史赛事检索页，默认不显示还没开的场次；日历页自己带
    ?include_calendar=1 把它们捞回来。meta 则刻意给两套数：total/ongoing/upcoming
    含排期行（日历要显示「即将开始 N 场」），catalog 只数已收录的真实赛次。
    """

    LIST = f"{BASE}/contests/"
    META = f"{BASE}/contests/meta/"

    def setUp(self):
        cache.clear()
        now = timezone.now()
        self.real = Contest.objects.create(
            platform=Platform.CODEFORCES, external_id="r", name="已赛完",
            series="Div. 2", is_rated=True,
            start_time=now - timedelta(days=4), end_time=now - timedelta(days=4, hours=-2))
        self.soon = Contest.objects.create(
            platform=Platform.CODEFORCES, external_id="c1", name="Codeforces Round 1200 (Div. 3)",
            series="Div. 3", is_rated=False, rated_source="calendar-feed",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=2))
        self.later = Contest.objects.create(
            platform=Platform.ATCODER, external_id="c2", name="abc999",
            series="ABC", is_rated=False, rated_source="calendar-feed",
            start_time=now + timedelta(days=9), end_time=now + timedelta(days=9, hours=2))

    def tearDown(self):
        cache.clear()

    def _ids(self, **qp):
        resp = self.client.get(self.LIST, qp)
        return {r["id"] for r in resp.data["results"]}

    def test_default_list_hides_calendar_rows(self):
        self.assertEqual(self._ids(), {self.real.pk})
        self.assertEqual(self._ids(status="upcoming"), set())

    def test_include_calendar_brings_them_back(self):
        self.assertEqual(self._ids(include_calendar="1"),
                         {self.real.pk, self.soon.pk, self.later.pk})
        self.assertEqual(self._ids(include_calendar="1", status="upcoming"),
                         {self.soon.pk, self.later.pk})
        # 月历的取数条件：跨月窗口按 end_after 筛，排期行必须在里面
        self.assertEqual(self._ids(include_calendar="1", platform="atcoder"),
                         {self.later.pk})

    def test_calendar_and_profile_flags_are_independent(self):
        """两个开关互不干扰：只放 anchor 不会顺带放出排期行。"""
        anchor = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="a", name="校内赛",
            is_rated=False, rated_source="profile-joined-history",
            start_time=timezone.now() - timedelta(days=40),
            end_time=timezone.now() - timedelta(days=40, hours=-2))
        self.assertEqual(self._ids(include_profile_only="1"),
                         {self.real.pk, anchor.pk})

    def test_meta_counts_schedule_rows_but_catalog_excludes_them(self):
        resp = self.client.get(self.META)
        data = resp.data
        self.assertEqual(data["upcoming"], 2)        # 两行排期都算「即将开始」
        self.assertEqual(data["ongoing"], 0)
        self.assertEqual(data["total"], 3)           # 含排期行的赛程总数
        self.assertEqual(data["catalog"], 1)         # 已收录的真实赛次
        self.assertEqual(data["finished"], 1)
        self.assertEqual(data["rated"], 1)
        by_key = {p["key"]: p["count"] for p in data["platforms"]}
        self.assertEqual(by_key["codeforces"], 2)    # 已赛 + 排期
        self.assertEqual(by_key["nowcoder"], 0)
        self.assertIn("ABC", data["series"])


class PublicProfileShowsUnratedTests(APITestCase):
    """个人主页参赛记录与牛客对齐：不计 Rating 的场次也展示，并带解题数。"""

    def setUp(self):
        cache.clear()
        self.user = make_user("profileu")
        self.acc = PlatformAccount.objects.create(
            user=self.user, platform=Platform.NOWCODER, handle="9001")
        now = timezone.now()
        self.rated = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="1", name="周赛",
            is_rated=True, start_time=now - timedelta(days=5))
        self.anchor = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="2", name="校内赛",
            is_rated=False, start_time=now - timedelta(days=300),
            rated_source="profile-joined-history",
            raw_meta={"source": "profile_joined"})
        for c, rank, ac, delta in ((self.rated, 10, 6, 41), (self.anchor, 4, 5, None)):
            Participation.objects.create(
                contest=c, platform_account=self.acc, handle="9001",
                handle_lower="9001", rank=rank, solved_count=ac,
                rating_delta=delta)

    def tearDown(self):
        cache.clear()

    def test_profile_lists_both_and_exposes_solved_count(self):
        resp = self.client.get(f"{BASE}/users/{self.user.pk}/profile/")
        self.assertEqual(resp.status_code, 200)
        rows = {r["contest_name"]: r for r in resp.data["participations"]}
        self.assertEqual(set(rows), {"周赛", "校内赛"})
        self.assertEqual(rows["校内赛"]["solved_count"], 5)
        self.assertFalse(rows["校内赛"]["contest_is_rated"])
        self.assertIsNone(rows["校内赛"]["rating_delta"])
        self.assertEqual(rows["周赛"]["rating_delta"], 41)
