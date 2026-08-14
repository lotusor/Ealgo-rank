"""
入库层测试，重点覆盖作弊账号排除 —— 这条一旦漏掉会直接污染学校积分。
"""

from django.test import TestCase

from apps.accounts.models import PlatformAccount, User, UserRole
from apps.common.models import ExcludeReason, Platform
from apps.contests.models import Contest, Participation
from apps.crawler.ingest import (detect_cheater, ingest_contest,
                                 rebind_unbound_participations)
from apps.schools.models import School


class CheaterDetectionTests(TestCase):
    """作弊标记识别。牛客的文案历史上有变体，正则要够宽。"""

    def test_standard_marker(self):
        is_c, name = detect_cheater("【已被标记为作弊】张三")
        self.assertTrue(is_c)
        self.assertEqual(name, "张三")

    def test_marker_variants(self):
        cases = [
            "【已被标记为作弊】abc",
            "[已被标记为作弊]abc",
            "【该用户已被标记为作弊】abc",
            "【已被平台标记为作弊】abc",
            "【已被标记为作弊，成绩无效】abc",
            "  【已被标记为作弊】 abc",
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                is_c, name = detect_cheater(raw)
                self.assertTrue(is_c, f"未识别: {raw}")
                self.assertEqual(name, "abc")

    def test_normal_name_untouched(self):
        for raw in ["张三", "【大佬】李四", "cheater_lover", "", None]:
            is_c, name = detect_cheater(raw)
            self.assertFalse(is_c, f"误判: {raw!r}")
        self.assertEqual(detect_cheater("【大佬】李四")[1], "【大佬】李四")


class IngestTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(name="测试大学", code="test-u")
        self.user = User.objects.create_user(
            username="stu1", password="pwd12345", school=self.school)
        self.acc = PlatformAccount.objects.create(
            user=self.user, platform=Platform.NOWCODER, handle="12345")
        # 作弊者也是本校已注册学生，必须落库留证但不计分
        self.cheat_user = User.objects.create_user(
            username="stu2", password="pwd12345", school=self.school)
        self.cheat_acc = PlatformAccount.objects.create(
            user=self.cheat_user, platform=Platform.NOWCODER, handle="66666")

        self.meta = {
            "real_contest_id": 108888,
            "name": "牛客周赛 Round 999",
            "start_time": "2026-08-01 19:00:00",
            "end_time": "2026-08-01 21:00:00",
            "duration_minutes": 120,
            "is_rated": True,
            "is_paid": False,
            "rated_source": "contest-info:category+uid+needCharge",
            "series": "牛客周赛",
        }
        self.detail = {
            "problems": [{"index": "A", "title": "签到", "problem_id": "p1",
                          "total_score": 100, "accepted_count": 900}],
            "ranks": [
                {"rank": 1, "uid": "12345", "user_name": "好学生",
                 "accepted_count": 4, "total_score": 400,
                 "penalty_time_ms": 100, "is_cheater": False,
                 "post_contest_append": False, "score_detail": [], "extra": {}},
                {"rank": 2, "uid": "66666",
                 "user_name": "【已被标记为作弊】坏学生",
                 "accepted_count": 4, "total_score": 400,
                 "penalty_time_ms": 90, "is_cheater": True,
                 "post_contest_append": False, "score_detail": [],
                 "extra": {"raw_user_name": "【已被标记为作弊】坏学生"}},
                {"rank": 3, "uid": "99999", "user_name": "路人甲",
                 "accepted_count": 3, "is_cheater": False,
                 "post_contest_append": False, "score_detail": [], "extra": {}},
                {"rank": 0, "uid": "12345678", "user_name": "赛后补交的",
                 "accepted_count": 5, "is_cheater": False,
                 "post_contest_append": True, "score_detail": [], "extra": {}},
            ],
        }

    def test_cheater_excluded_from_scoring(self):
        stats = ingest_contest(Platform.NOWCODER, self.meta, self.detail)

        self.assertFalse(stats["skipped"])
        self.assertEqual(stats["cheaters"], 1)
        self.assertEqual(stats["matched"], 2)      # 好学生 + 坏学生
        self.assertEqual(stats["countable"], 1)    # 只有好学生计分

        cheat = Participation.objects.get(handle="66666")
        self.assertTrue(cheat.is_excluded)
        self.assertEqual(cheat.exclude_reason, ExcludeReason.CHEATER)
        # 展示用昵称已剥离前缀，原文另存供审计
        self.assertEqual(cheat.display_name, "坏学生")
        self.assertEqual(cheat.raw_display_name, "【已被标记为作弊】坏学生")

        good = Participation.objects.get(handle="12345")
        self.assertFalse(good.is_excluded)
        self.assertEqual(good.exclude_reason, "")

        # countable() 是积分引擎唯一入口，必须只剩好学生
        countable = Participation.objects.countable()
        self.assertEqual(countable.count(), 1)
        self.assertEqual(countable.first().handle, "12345")

    def test_unrelated_participants_not_stored(self):
        ingest_contest(Platform.NOWCODER, self.meta, self.detail)
        # 路人甲未绑定且非作弊 -> 不落库
        self.assertFalse(Participation.objects.filter(handle="99999").exists())

    def test_contest_counters(self):
        ingest_contest(Platform.NOWCODER, self.meta, self.detail)
        c = Contest.objects.get(platform=Platform.NOWCODER, external_id="108888")
        self.assertEqual(c.participant_count, 4)
        self.assertEqual(c.cheater_count, 1)
        self.assertEqual(c.valid_participant_count, 1)
        self.assertTrue(c.countable)

    def test_fallback_detects_cheater_without_flag(self):
        """旧版爬虫产出的 JSON 没有 is_cheater 字段，入库层要能兜住。"""
        detail = {"problems": [], "ranks": [
            {"rank": 1, "uid": "66666", "user_name": "【已被标记为作弊】坏学生",
             "post_contest_append": False, "score_detail": [], "extra": {}},
        ]}
        stats = ingest_contest(Platform.NOWCODER, self.meta, detail)
        self.assertEqual(stats["cheaters"], 1)
        self.assertTrue(Participation.objects.get(handle="66666").is_excluded)

    def test_paid_contest_skipped(self):
        meta = {**self.meta, "real_contest_id": 133876, "is_paid": True}
        stats = ingest_contest(Platform.NOWCODER, meta, self.detail)
        self.assertTrue(stats["skipped"])
        self.assertFalse(Contest.objects.filter(external_id="133876").exists())

    def test_unrated_contest_skipped(self):
        meta = {**self.meta, "real_contest_id": 137532, "is_rated": False}
        stats = ingest_contest(Platform.NOWCODER, meta, self.detail)
        self.assertTrue(stats["skipped"])

    def test_rebind_does_not_revive_cheater(self):
        """作弊记录在学生重新绑定后依然保持排除。"""
        ingest_contest(Platform.NOWCODER, self.meta, self.detail)
        # 模拟解绑后重绑
        Participation.objects.filter(handle="66666").update(
            platform_account=None)
        rebind_unbound_participations(self.cheat_acc)
        cheat = Participation.objects.get(handle="66666")
        self.assertTrue(cheat.is_excluded)
        self.assertEqual(cheat.exclude_reason, ExcludeReason.CHEATER)


class SchoolBindingTests(TestCase):
    """学校归属只认平台账号绑定，不读榜单里的学校字段。"""

    def test_school_synced_to_platform_accounts(self):
        school = School.objects.create(name="绑定大学", code="bind-u")
        user = User.objects.create_user(username="s1", password="pwd12345")
        acc = PlatformAccount.objects.create(
            user=user, platform=Platform.CODEFORCES, handle="Tourist")
        self.assertIsNone(acc.school_id)

        user.school = school
        user.save()
        user.sync_platform_accounts_school()

        acc.refresh_from_db()
        self.assertEqual(acc.school_id, school.pk)

    def test_handle_lower_normalized(self):
        user = User.objects.create_user(username="s2", password="pwd12345")
        acc = PlatformAccount.objects.create(
            user=user, platform=Platform.CODEFORCES, handle="TourIST")
        self.assertEqual(acc.handle_lower, "tourist")


from rest_framework.test import APITestCase

from apps.crawler.models import CrawlJob

BASE = "/api/v1"
CRAWL_LIST = f"{BASE}/crawl-jobs/"
CRAWL_TRIGGER = f"{BASE}/crawl-jobs/trigger/"


def _make_crawl_user(username, role=UserRole.USER, school=None, password="Test1234!"):
    return User.objects.create_user(
        username=username, password=password, role=role, school=school)


class CrawlerPermissionTests(APITestCase):
    """#3 爬虫权限：爬虫属系统底层信息，仅超级管理员可访问与操作。"""

    def setUp(self):
        self.admin = _make_crawl_user("crawl_admin", role=UserRole.SCHOOL_ADMIN)
        self.super = _make_crawl_user("crawl_super", role=UserRole.SUPER_ADMIN)
        CrawlJob.objects.create(platform=Platform.CODEFORCES,
                                triggered_by=self.super)

    def test_admin_list_forbidden(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(CRAWL_LIST)
        self.assertEqual(resp.status_code, 403)

    def test_admin_trigger_forbidden(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(CRAWL_TRIGGER, {"platform": "codeforces"},
                                format="json")
        self.assertEqual(resp.status_code, 403)

    def test_super_list_ok(self):
        self.client.force_authenticate(self.super)
        resp = self.client.get(CRAWL_LIST)
        self.assertEqual(resp.status_code, 200)

    def test_super_trigger_ok(self):
        self.client.force_authenticate(self.super)
        resp = self.client.post(CRAWL_TRIGGER, {"platform": "codeforces"},
                                format="json")
        # 触发接口立即返回 201（后台派发，broker 不可达不影响返回）
        self.assertEqual(resp.status_code, 201, resp.content)


from apps.crawler.models import CrawlConfig
from apps.crawler.tasks import (
    auto_crawl_task,
    create_crawl_job,
    enqueue_crawl,
)


class CrawlDedupTests(TestCase):
    """#3 防重复爬取：同一平台 + 相同参数在去重窗口内已有进行中任务时不再重复派发。"""

    def test_dedup_skips_active_duplicate(self):
        params = {"count": 20, "mode": "rating"}
        j1, created1 = create_crawl_job(Platform.CODEFORCES, params)
        self.assertTrue(created1)
        j2, created2 = create_crawl_job(Platform.CODEFORCES, params)
        self.assertFalse(created2)
        self.assertEqual(j1.pk, j2.pk)
        self.assertEqual(CrawlJob.objects.count(), 1)

    def test_different_params_create_separate_jobs(self):
        create_crawl_job(Platform.CODEFORCES, {"count": 20, "mode": "rating"})
        create_crawl_job(Platform.CODEFORCES, {"count": 50, "mode": "rating"})
        self.assertEqual(CrawlJob.objects.count(), 2)

    def test_only_pending_running_blocked(self):
        # 已失败的任务不阻断新的同参数爬取（允许重试）
        j1, _ = create_crawl_job(Platform.ATCODER, {"count": 10})
        CrawlJob.objects.filter(pk=j1.pk).update(status=CrawlJob.Status.FAILED)
        j2, created2 = create_crawl_job(Platform.ATCODER, {"count": 10})
        self.assertTrue(created2)
        self.assertEqual(CrawlJob.objects.count(), 2)

    def test_enqueue_creates_job(self):
        before = CrawlJob.objects.count()
        job = enqueue_crawl(Platform.CODEFORCES, {"count": 20, "mode": "rating"})
        self.assertIsNotNone(job)
        self.assertEqual(CrawlJob.objects.count(), before + 1)


class AutoCrawlTaskTests(TestCase):
    """#2 定时自动激活爬虫：读取 CrawlConfig，按配置为三平台派发。"""

    def test_disabled_skips(self):
        cfg = CrawlConfig.get_config()
        cfg.enabled = False
        cfg.save()
        CrawlJob.objects.all().delete()
        result = auto_crawl_task()
        self.assertTrue(result.get("skipped"))
        self.assertEqual(CrawlJob.objects.count(), 0)

    def test_enabled_dispatches_all_platforms(self):
        cfg = CrawlConfig.get_config()
        cfg.enabled = True
        cfg.cf_count = 5
        cfg.atcoder_count = 5
        cfg.nowcoder_months_back = 1
        cfg.save()
        CrawlJob.objects.all().delete()
        result = auto_crawl_task()
        self.assertIn("dispatched", result)
        # 三大平台各一份爬取任务（broker 不可达时任务会被标记 failed，但已创建）
        self.assertEqual(CrawlJob.objects.count(), 3)
        self.assertEqual(
            set(CrawlJob.objects.values_list("platform", flat=True)),
            {Platform.CODEFORCES, Platform.ATCODER, Platform.NOWCODER},
        )
