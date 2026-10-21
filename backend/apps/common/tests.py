"""公开站点统计端点（首页数字看板）+ 平台注册表护栏。"""
from dataclasses import replace
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import PlatformAccount
from apps.common import platforms
from apps.common.models import Platform
from apps.common.platforms import (RATED_PREVIEWS, PLATFORM_SPECS,
                                   calendar_specs, crawl_choices,
                                   crawlable_specs, validate_registry)
from apps.contests.models import Contest, Participation
from apps.crawler.ingest import CALENDAR_RATED_SOURCE
from apps.ranking.engine import contest_perf_base
from apps.schools.models import School, ScoreConfig


class PublicStatsViewTests(TestCase):
    def test_allow_any_and_counts(self):
        School.objects.create(name="统计大学", code="statu", short_name="统")
        get_user_model().objects.create_user(username="stat1", password="Test1234!")
        resp = self.client.get("/api/v1/stats/")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data["schools"], 1)
        self.assertGreaterEqual(resp.data["users"], 1)
        self.assertEqual(
            set(resp.data.keys()),
            {"schools", "contests", "users", "participations", "platforms"},
        )

    def test_platforms_breakdown_covers_every_registered_platform(self):
        """首页「支持的平台」卡片按这份真实计数出数，不再写死 712/2103 这类假数字。"""
        resp = self.client.get("/api/v1/stats/")
        got = {p["key"] for p in resp.data["platforms"]}
        self.assertEqual(got, {p.value for p in Platform})
        for row in resp.data["platforms"]:
            self.assertIn(row["scoring"], (True, False))
            self.assertGreaterEqual(row["contests"], 0)
            self.assertLessEqual(row["contests"], resp.data["contests"],
                                 "逐平台计数不得多于总数（排期行不算收录）")

    def test_contests_exclude_display_only_rows(self):
        """首页「比赛数」只算真正收录的赛次。

        锚点赛次（§0.25）与日历排期行（§0.26）都是派生行，计进来会让看板虚高——
        锚点已经让它漂移过一次（生产 total 180 → 212）。
        """
        from datetime import timedelta

        from django.utils import timezone

        from apps.common.models import Platform
        from apps.contests.models import Contest
        from apps.crawler.ingest import CALENDAR_RATED_SOURCE, PROFILE_RATED_SOURCE

        now = timezone.now()
        Contest.objects.create(platform=Platform.CODEFORCES, external_id="real",
                               name="真比赛", is_rated=True,
                               start_time=now - timedelta(days=2),
                               end_time=now - timedelta(days=2, hours=-2))
        for eid, src in (("anchor", PROFILE_RATED_SOURCE),
                         ("cal", CALENDAR_RATED_SOURCE)):
            Contest.objects.create(platform=Platform.NOWCODER, external_id=eid,
                                   name=eid, is_rated=False, rated_source=src,
                                   start_time=now + timedelta(days=1),
                                   end_time=now + timedelta(days=1, hours=2))
        resp = self.client.get("/api/v1/stats/")
        self.assertEqual(resp.data["contests"], 1)


class FirstMessageTests(TestCase):
    """统一异常处理：字段级校验错误的第一条原因提升为 detail（2026-09-13）。"""

    def test_first_message_forms(self):
        from apps.common.exceptions import _first_message

        cases = [
            # (输入, 期望)
            ({"school": ["你本月已提交过申请，请下月再试"]},
             "你本月已提交过申请，请下月再试"),
            # serializer 级 validate() 的 non_field_errors 优先
            ({"school": ["字段级"], "non_field_errors": ["非字段级"]},
             "非字段级"),
            # 嵌套 serializer（dict 套 dict）
            ({"profile": {"name": ["名字太长"]}}, "名字太长"),
            # list 内嵌 dict
            ([{"a": ["深层"]}], "深层"),
            # 字符串
            ("直接字符串", "直接字符串"),
            # 空结构
            ({}, ""),
        ]
        for data, expect in cases:
            with self.subTest(data=data):
                self.assertEqual(_first_message(data), expect)

    def test_handler_promotes_first_reason(self):
        """端到端：触发字段级校验错误，detail 应为具体原因而非通用文案。"""
        from rest_framework import serializers, viewsets
        from rest_framework.permissions import AllowAny
        from rest_framework.test import APIRequestFactory

        from apps.common.exceptions import api_exception_handler

        class _Ser(serializers.Serializer):
            school = serializers.CharField()

            def validate_school(self, v):
                raise serializers.ValidationError("你本月已提交过申请，请下月再试")

        class _View(viewsets.ViewSet):
            permission_classes = [AllowAny]

            def create(self, request):
                ser = _Ser(data=request.data)
                ser.is_valid(raise_exception=True)
                return serializers.Response({})

        factory = APIRequestFactory()
        req = factory.post("/", {"school": "x"}, format="json")
        view = _View.as_view({"post": "create"})
        # DRF dispatch 会捕获 ValidationError 并走配置的统一 handler，
        # 直接返回 400 响应（不抛异常）
        resp = view(req)
        resp.render()  # 显式渲染（test client 之外不自动渲染）
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["detail"], "你本月已提交过申请，请下月再试")
        self.assertEqual(resp.data["code"], "validation_error")
        # errors 明细保留
        self.assertIn("school", resp.data["errors"])


class PlatformRegistryTests(TestCase):
    """平台注册表的对齐护栏（2026-09-26 接洛谷时引入）。

    本仓库没有 CI，「加了平台忘了配下一处」过去只会在线上表现为数据不对
    （未知平台按兜底基线计分、日历恒判不计分、前端渲染成别的平台的颜色）。
    这几条用例 + `validate_registry()` 就是把它换成失败先于出错数据。
    """

    def test_enum_and_registry_cover_each_other(self):
        self.assertEqual({s.value for s in PLATFORM_SPECS},
                         {p.value for p in Platform},
                         "枚举与注册表必须一一对应")
        self.assertTrue(validate_registry())

    def test_labels_match_the_enum(self):
        for s in PLATFORM_SPECS:
            with self.subTest(platform=s.value):
                self.assertEqual(s.label, Platform(s.value).label)

    def test_calendar_platform_declares_a_rated_source(self):
        for s in calendar_specs():
            with self.subTest(platform=s.value):
                self.assertIn(s.rated_preview, RATED_PREVIEWS[1:],
                              "进日历却没声明判定源 = 该平台永远显示「不计分」")

    def test_only_crawlable_platforms_can_be_triggered(self):
        choices = dict(crawl_choices())
        self.assertEqual(set(choices), {s.value for s in crawlable_specs()})
        self.assertNotIn(Platform.LUOGU, choices,
                         "只做展示的平台进了触发接口，会先落一条没人消费的 job")

    def test_validate_registry_rejects_a_missing_spec(self):
        """漏注册要炸在启动期，而不是等这个平台真的被用到才静默给错数据。"""
        trimmed = PLATFORM_SPECS[:-1]
        with mock.patch.object(platforms, "PLATFORM_SPECS", trimmed), \
                mock.patch.object(platforms, "_BY_VALUE",
                                  {s.value: s for s in trimmed}):
            with self.assertRaises(ImproperlyConfigured) as cm:
                validate_registry()
        self.assertIn("不一致", str(cm.exception))

    def test_validate_registry_rejects_scoring_without_base(self):
        """声明计分却没有 perf_base / 平台系数列 → 表现分会静默落到别处的数。"""
        broken = tuple(
            replace(s, scoring=True) if s.value == Platform.LUOGU else s
            for s in PLATFORM_SPECS)
        with mock.patch.object(platforms, "PLATFORM_SPECS", broken), \
                mock.patch.object(platforms, "_BY_VALUE",
                                  {s.value: s for s in broken}):
            with self.assertRaises(ImproperlyConfigured) as cm:
                validate_registry()
        msg = str(cm.exception)
        self.assertIn("perf_base", msg)
        self.assertIn("平台系数列", msg)
        self.assertIn("必须可绑定", msg)
        self.assertIn(Platform.LUOGU.value, msg, "报错要点名是哪个平台")


class DisplayOnlyPlatformTests(TestCase):
    """只做日历展示的平台（洛谷）不得进入积分链路的任何一环。

    与 §0.28 的「展示型赛次靠 rated_source 隔离」是两条不同维度的闸：那条管
    行的来历，这条管平台本身 —— 万一将来有人给这类平台补进了榜单行，也不至于
    在没人察觉的情况下改变排名。
    """

    def setUp(self):
        self.now = timezone.now()
        self.user = get_user_model().objects.create_user(
            username="lg-user", password="Test1234!")
        self.acc = PlatformAccount.objects.create(
            user=self.user, platform=Platform.LUOGU, handle="1001")

    def _contest(self, **kw):
        kw.setdefault("platform", Platform.LUOGU)
        kw.setdefault("external_id", "900")
        kw.setdefault("name", "洛谷月赛")
        kw.setdefault("start_time", self.now - timedelta(days=2))
        kw.setdefault("end_time", self.now - timedelta(days=1))
        return Contest.objects.create(**kw)

    def test_rated_row_of_a_display_platform_is_not_countable(self):
        c = self._contest(is_rated=True, rated_source=CALENDAR_RATED_SOURCE)
        p = Participation.objects.create(contest=c, platform_account=self.acc,
                                         handle="1001", rank=1)
        self.assertFalse(c.countable)
        self.assertNotIn(p, Participation.objects.countable())

    def test_even_a_mis_ingested_row_is_still_excluded(self):
        """把 rated_source 也写错成「榜单来的」，平台这一道闸仍然挡住。"""
        c = self._contest(is_rated=True, rated_source="luogu.contest/list")
        p = Participation.objects.create(contest=c, platform_account=self.acc,
                                         handle="1001", rank=1)
        self.assertNotIn(p, Participation.objects.countable())

    def test_scoring_platform_is_unaffected_by_the_guard(self):
        """护栏不能改变三平台既有口径：同样的行，CF 照样 countable。"""
        cf = PlatformAccount.objects.create(user=self.user,
                                            platform=Platform.CODEFORCES,
                                            handle="lg_user")
        c = self._contest(platform=Platform.CODEFORCES, external_id="2200",
                          is_rated=True,
                          rated_source="contest.ratingChanges")
        p = Participation.objects.create(contest=c, platform_account=cf,
                                         handle="lg_user", rank=1)
        self.assertIn(p, Participation.objects.countable())

    def test_display_platform_has_no_perf_base_or_factor(self):
        """没有基线也没有系数：算分时必须抛，而不是拿兜底值静默参与排名。"""
        c = self._contest(is_rated=True)
        with self.assertRaises(ValueError):
            contest_perf_base(c)
        with self.assertRaises(ValueError):
            ScoreConfig.get_config().platform_factor(Platform.LUOGU)
