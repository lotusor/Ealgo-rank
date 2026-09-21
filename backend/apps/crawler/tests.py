"""
入库层测试，重点覆盖作弊账号排除 —— 这条一旦漏掉会直接污染学校积分。
"""

from django.test import TestCase

from apps.accounts.models import PlatformAccount, User, UserRole
from apps.common.models import ExcludeReason, Platform
from apps.contests.models import Contest, Participation
from apps.crawler.ingest import (detect_cheater, ingest_contest,
                                 rebind_unbound_participations,
                                 fill_participated_contests)
from apps.schools.models import (AtCoderAffiliationAlias, School,
                              normalize_atcoder_affiliation)


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

    def test_unbound_cheater_not_stored_but_counted(self):
        """未绑定的作弊路人：明细不落库（2026-09-07 决策，控管理成本），
        但计数仍进 Contest.cheater_count 聚合列。"""
        detail = {"problems": [], "ranks": [
            {"rank": 5, "uid": "77777", "user_name": "【已被标记为作弊】路人乙",
             "is_cheater": True, "post_contest_append": False,
             "score_detail": [], "extra": {}},
            {"rank": 6, "uid": "88888", "user_name": "路人丙",
             "is_cheater": False, "post_contest_append": False,
             "score_detail": [], "extra": {}},
        ]}
        stats = ingest_contest(Platform.NOWCODER, self.meta, detail)
        # 明细一律不落
        self.assertFalse(Participation.objects.filter(handle="77777").exists())
        self.assertFalse(Participation.objects.filter(handle="88888").exists())
        # 统计照常：cheaters 计 1，matched 计 0
        self.assertEqual(stats["cheaters"], 1)
        self.assertEqual(stats["matched"], 0)
        c = Contest.objects.get(external_id="108888")
        self.assertEqual(c.cheater_count, 1)

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

    def test_paid_contest_ingested(self):
        """付费但 rated 的比赛应正常入库并计分（用户决策：只要 rated 就收录）。"""
        meta = {**self.meta, "real_contest_id": 133876, "is_paid": True}
        stats = ingest_contest(Platform.NOWCODER, meta, self.detail)
        self.assertFalse(stats.get("skipped"))
        c = Contest.objects.get(external_id="133876")
        self.assertTrue(c.is_paid)
        self.assertTrue(c.countable)

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
    crawl_nowcoder,
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


class AtCoderAffiliationNormalizationTests(TestCase):
    """M2：AtCoder affiliation 归一化仅参考/核对，不参与学校归属。

    核心约束：归一化结果写入 Participation.extra 供管理员核对，但绝不能改
    PlatformAccount.school（学校归属只认绑定关系）。
    """

    def setUp(self):
        self.school = School.objects.create(name="东京工业大学", code="titech")
        self.user = User.objects.create_user(
            username="atc1", password="pwd12345", school=self.school)
        # 学生绑定的平台账号归属「测试大学」，与 AtCoder 自填机构无关
        self.bound_school = School.objects.create(name="测试大学", code="test-u")
        self.user.school = self.bound_school
        self.user.save()
        self.user.sync_platform_accounts_school()
        self.acc = PlatformAccount.objects.create(
            user=self.user, platform=Platform.ATCODER, handle="tourist_titech")
        self.assertEqual(self.acc.school_id, self.bound_school.pk)

        self.alias = AtCoderAffiliationAlias.objects.create(
            raw_affiliation="Tokyo Institute of Technology",
            school=self.school, canonical_name="东京工业大学")
        self.no_school_alias = AtCoderAffiliationAlias.objects.create(
            raw_affiliation="Some Club", canonical_name="某社团", school=None)

    def _ingest_atcoder(self, ranks):
        meta = {
            "real_contest_id": 404555, "name": "AtCoder ABC 999",
            "start_time": "2026-08-01 21:00:00",
            "end_time": "2026-08-01 22:40:00", "duration_minutes": 100,
            "is_rated": True, "is_paid": False,
            "rated_source": "contest-info", "series": "AtCoder Beginner",
        }
        detail = {"problems": [], "ranks": ranks}
        return ingest_contest(Platform.ATCODER, meta, detail)

    def test_affiliation_normalized_into_extra(self):
        stats = self._ingest_atcoder([{
            "rank": 1, "uid": "tourist_titech", "user_name": " tourist ",
            "accepted_count": 5, "is_cheater": False,
            "post_contest_append": False, "score_detail": [],
            "extra": {"affiliation": "tokyo institute of technology"},
        }])
        self.assertFalse(stats["skipped"])
        p = Participation.objects.get(handle="tourist_titech")
        norm = p.extra.get("affiliation_normalized")
        self.assertIsNotNone(norm)
        self.assertEqual(norm["school_id"], self.school.pk)
        self.assertEqual(norm["school_name"], "东京工业大学")
        self.assertEqual(norm["raw"], "Tokyo Institute of Technology")
        # 大小写/空格归一：落库 raw 用别名表原始写法
        self.assertEqual(norm["raw"], self.alias.raw_affiliation)

    def test_attribution_untouched(self):
        """归一化不得改变平台账号的学校归属。"""
        self._ingest_atcoder([{
            "rank": 1, "uid": "tourist_titech", "user_name": " tourist ",
            "accepted_count": 5, "is_cheater": False,
            "post_contest_append": False, "score_detail": [],
            "extra": {"affiliation": "Tokyo Institute of Technology"},
        }])
        # 即便 AtCoder 自填机构指向「东京工业大学」，账号归属仍是「测试大学」
        self.acc.refresh_from_db()
        self.assertEqual(self.acc.school_id, self.bound_school.pk)

    def test_no_match_writes_nothing(self):
        self._ingest_atcoder([{
            "rank": 1, "uid": "tourist_titech", "user_name": " tourist ",
            "accepted_count": 5, "is_cheater": False,
            "post_contest_append": False, "score_detail": [],
            "extra": {"affiliation": "Unknown Org"},
        }])
        p = Participation.objects.get(handle="tourist_titech")
        self.assertNotIn("affiliation_normalized", p.extra)

    def test_alias_without_school_uses_canonical_name(self):
        self._ingest_atcoder([{
            "rank": 1, "uid": "tourist_titech", "user_name": " tourist ",
            "accepted_count": 5, "is_cheater": False,
            "post_contest_append": False, "score_detail": [],
            "extra": {"affiliation": "some club"},
        }])
        p = Participation.objects.get(handle="tourist_titech")
        norm = p.extra["affiliation_normalized"]
        self.assertIsNone(norm["school_id"])
        self.assertEqual(norm["canonical_name"], "某社团")

    def test_normalize_helper_directly(self):
        # 直接调用工具函数，确认无 alias_map 时也能查库
        res = normalize_atcoder_affiliation("TOKYO INSTITUTE OF TECHNOLOGY")
        self.assertEqual(res["school_name"], "东京工业大学")
        self.assertIsNone(normalize_atcoder_affiliation(""))
        self.assertIsNone(normalize_atcoder_affiliation("No Such Org"))


from unittest import mock  # noqa: E402

from django.core.management import call_command  # noqa: E402

import apps.crawler.tasks as tasks_mod  # noqa: E402
import apps.crawler.management.commands.rebuild_participation_index as rebuild_mod  # noqa: E402
from apps.crawler.tasks import crawl_codeforces  # noqa: E402


class _FakeCF:
    """替代 CodeforcesScraper：不联网，返回受控比赛列表与明细。"""

    def fetch_contests(self):
        return _FAKE_CF_LIST

    def parse_contests(self, lst):
        return lst

    def filter_contests(self, contests, rated_only=True, exclude_paid=True):
        return [c for c in contests if c.get("is_rated") and not c.get("is_paid")]

    def scrape_contest_detail(self, contest_id, mode="rating", handles=None,
                              cache_dir=None, cache_ttl_hours=168, **kwargs):
        return {
            "problems": [{"index": "A", "title": "t", "problem_id": f"{contest_id}-A"}],
            "ranks": [{"rank": 1, "uid": "someone", "user_name": "someone",
                       "is_cheater": False, "post_contest_append": False,
                       "score_detail": [], "extra": {}}],
            "rank_count": 1, "valid_rank_count": 1,
            "rank_source": "ratingChanges", "crawled_at": "2026-08-14T00:00:00",
        }


_FAKE_CF_LIST = [
    {"contest_id": 111, "real_contest_id": 111, "name": "CF 111",
     "is_rated": True, "is_paid": False, "is_future": False,
     "phase": "FINISHED"},
    {"contest_id": 222, "real_contest_id": 222, "name": "CF 222",
     "is_rated": True, "is_paid": False, "is_future": False,
     "phase": "FINISHED"},
]


class RelevantContestFilterTests(TestCase):
    """A：预筛 = 窗口 ∪ 索引历史（窗口内的比赛 + 用户历史参加的比赛都要抓）。"""

    def _make_cf_account(self, username, participated):
        user = User.objects.create_user(username=username, password="pwd12345")
        return PlatformAccount.objects.create(
            user=user, platform=Platform.CODEFORCES, handle=username,
            participated_contests=participated)

    def test_window_plus_index_crawled(self):
        # cfr1 索引里只有 111；但 111/222 都在最近窗口内，应一起抓（窗口∪索引）
        self._make_cf_account("cfr1", ["111"])
        with mock.patch.object(tasks_mod, "_load_scraper", return_value=_FakeCF()):
            crawl_codeforces(count=10, mode="rating")
        contests = Contest.objects.filter(platform=Platform.CODEFORCES)
        self.assertEqual(contests.count(), 2)
        ids = {c.external_id for c in contests}
        self.assertEqual(ids, {"111", "222"})

    def test_force_crawls_all(self):
        self._make_cf_account("cfr2", ["111"])
        with mock.patch.object(tasks_mod, "_load_scraper", return_value=_FakeCF()):
            crawl_codeforces(count=10, mode="rating", force=True)
        self.assertEqual(
            Contest.objects.filter(platform=Platform.CODEFORCES).count(), 2)


class ParticipationIndexUpdateTests(TestCase):
    """A：入库命中账号时，增量维护其参与比赛索引。"""

    def test_ingest_updates_account_index(self):
        school = School.objects.create(name="索引大学", code="idx-u")
        user = User.objects.create_user(username="idx1", password="pwd12345",
                                        school=school)
        acc = PlatformAccount.objects.create(
            user=user, platform=Platform.NOWCODER, handle="idxhandle",
            participated_contests=[])
        meta = {"real_contest_id": 555111, "name": "牛客周赛 Round X",
                "start_time": "2026-08-01 19:00:00",
                "end_time": "2026-08-01 21:00:00", "duration_minutes": 120,
                "is_rated": True, "is_paid": False}
        detail = {"problems": [], "ranks": [
            {"rank": 1, "uid": "idxhandle", "user_name": "idx",
             "accepted_count": 1, "is_cheater": False,
             "post_contest_append": False, "score_detail": [], "extra": {}},
        ]}
        ingest_contest(Platform.NOWCODER, meta, detail)
        acc.refresh_from_db()
        self.assertIn("555111", acc.participated_contests)

    def test_reingest_preserves_backfilled_rating(self):
        """重新爬取（榜单无 rating）不得把回填的 rating 覆盖为 None
        （2026-09-03 事故：#71 重爬后全部牛客 rating 变 None）。"""
        school = School.objects.create(name="保rating大学", code="keep-r")
        user = User.objects.create_user(username="keep1", password="Test1234!",
                                        school=school)
        acc = PlatformAccount.objects.create(
            user=user, platform=Platform.NOWCODER, handle="keeprank",
            handle_lower="keeprank")
        meta = {"real_contest_id": 555222, "name": "牛客周赛 Round X2",
                "start_time": "2026-08-01 19:00:00",
                "end_time": "2026-08-01 21:00:00", "duration_minutes": 120,
                "is_rated": True, "is_paid": False}
        detail = {"problems": [], "ranks": [
            {"rank": 10, "uid": "keeprank", "user_name": "keep",
             "accepted_count": 2, "is_cheater": False,
             "post_contest_append": False, "score_detail": [], "extra": {}},
        ]}
        ingest_contest(Platform.NOWCODER, meta, detail)
        p = Participation.objects.get(contest__external_id="555222")
        # 模拟 rating-history 回填
        p.new_rating = 1208
        p.rating_delta = 46
        p.old_rating = 1162
        p.save()
        # 重新爬取同一场：榜单仍不含 rating 字段
        detail2 = {"problems": [], "ranks": [
            {"rank": 10, "uid": "keeprank", "user_name": "keep",
             "accepted_count": 2, "is_cheater": False,
             "post_contest_append": False, "score_detail": [], "extra": {}},
        ]}
        ingest_contest(Platform.NOWCODER, meta, detail2)
        p.refresh_from_db()
        self.assertEqual(p.new_rating, 1208)
        self.assertEqual(p.rating_delta, 46)
        self.assertEqual(p.old_rating, 1162)
        # rank 等榜单字段仍正常更新
        self.assertEqual(p.rank, 10)


class RebuildIndexCommandTests(TestCase):
    """A：rebuild 命令 = 参与记录表回填 ∪ 官方个人历史接口补全。"""

    def test_command_unions_participation_and_history(self):
        user = User.objects.create_user(username="rb1", password="pwd12345")
        acc = PlatformAccount.objects.create(
            user=user, platform=Platform.CODEFORCES, handle="rbhandle",
            participated_contests=[])
        # ① 参与记录表已有一条（external_id 999）
        contest = Contest.objects.create(
            platform=Platform.CODEFORCES, external_id="999", name="c999",
            is_rated=True, is_paid=False)
        Participation.objects.create(
            contest=contest, platform_account=acc, handle="rbhandle",
            handle_lower="rbhandle")

        fake_cf = mock.MagicMock()
        fake_cf.user_rating_contest_ids.return_value = ["1000"]  # ② 历史接口
        fake_atc = mock.MagicMock()

        with mock.patch.object(rebuild_mod, "CodeforcesScraper",
                               return_value=fake_cf), \
                mock.patch.object(rebuild_mod, "AtCoderScraper",
                                  return_value=fake_atc):
            call_command("rebuild_participation_index", "--platform", "codeforces")

        acc.refresh_from_db()
        self.assertIn("999", acc.participated_contests)
        self.assertIn("1000", acc.participated_contests)
        fake_cf.user_rating_contest_ids.assert_called_once_with("rbhandle")


class AtCoderHistoryParseTests(TestCase):
    """A：AtCoder 个人历史接口对旧比赛返回子域名，需归一化对齐 external_id。"""

    def test_history_normalizes_legacy_domain(self):
        from atcoder_scraper import AtCoderScraper
        sc = AtCoderScraper()
        canned = [
            {"ContestScreenName": "agc004.contest.atcoder.jp"},
            {"ContestScreenName": "abc470"},
            {"ContestScreenName": "arc061.contest.atcoder.jp"},
        ]

        class _Resp:
            def json(self):
                return canned
        with mock.patch.object(sc, "_get", return_value=_Resp()):
            ids = sc.user_history_contest_ids("someone")
        self.assertEqual(ids, ["agc004", "abc470", "arc061"])


class FillParticipatedContestsTests(TestCase):
    """绑定后补全参与比赛索引（解决冷启动预筛死锁）。"""

    def _make_cf_account(self, username, participated=None):
        user = User.objects.create_user(username=username, password="pwd12345")
        return PlatformAccount.objects.create(
            user=user, platform=Platform.CODEFORCES, handle=username,
            participated_contests=participated or [])

    def test_cf_fills_index(self):
        acc = self._make_cf_account("fillcf1")
        fake_cf = mock.MagicMock()
        fake_cf.user_rating_contest_ids.return_value = ["111", "222"]
        with mock.patch("cf_scraper.CodeforcesScraper", return_value=fake_cf):
            updated, n = fill_participated_contests(acc)
        self.assertTrue(updated)
        self.assertEqual(n, 2)
        acc.refresh_from_db()
        self.assertIn("111", acc.participated_contests)
        self.assertIn("222", acc.participated_contests)

    def test_union_keeps_existing(self):
        acc = self._make_cf_account("fillcf2", participated=["999"])
        fake_cf = mock.MagicMock()
        fake_cf.user_rating_contest_ids.return_value = ["111"]
        with mock.patch("cf_scraper.CodeforcesScraper", return_value=fake_cf):
            fill_participated_contests(acc)
        acc.refresh_from_db()
        self.assertIn("999", acc.participated_contests)
        self.assertIn("111", acc.participated_contests)

    def test_nowcoder_returns_false(self):
        user = User.objects.create_user(username="fillnc", password="pwd12345")
        acc = PlatformAccount.objects.create(
            user=user, platform=Platform.NOWCODER, handle="123456",
            participated_contests=[])
        updated, n = fill_participated_contests(acc)
        self.assertFalse(updated)
        self.assertEqual(n, 0)


class _FakeNC:
    """替代 NowCoderScraper：受控比赛列表，验证截断方向与未结束比赛过滤。"""

    def __init__(self, contests, rating_history=None):
        self._contests = contests
        self._rating_history = rating_history or {}
        self.scraped = []  # 记录 scrape_contest_detail 被调用的比赛 id
        self.ttl_calls = []  # (比赛 id, 传入的 cache_ttl_hours)

    def init_session(self):
        pass

    def user_rating_history(self, handle):
        return self._rating_history.get(handle, [])

    def fetch_contests(self, ym):
        return [c for c in self._contests if (c.get("start_time") or "")[:7] == ym]

    def parse_contests(self, lst, only_nowcoder=True):
        return lst

    def filter_contests(self, contests, rated_only=True, exclude_paid=True):
        return [c for c in contests if c.get("is_rated")]

    def scrape_contest_detail(self, rid, filter_post_contest=False,
                              exclude_cheaters=False, cache_dir=None,
                              cache_ttl_hours=168, **kwargs):
        self.scraped.append(str(rid))
        self.ttl_calls.append((str(rid), cache_ttl_hours))
        return {"problems": [], "ranks": [], "rank_count": 0,
                "valid_rank_count": 0, "rank_source": "fake",
                "crawled_at": "2026-08-29T00:00:00"}


class NowcoderWindowTests(TestCase):
    """牛客窗口处理：截断必须保最新（历史 bug：[:50] 砍掉尾部最新比赛）、
    未结束比赛不入库（防脏数据 + 缓存不自愈）。"""

    @staticmethod
    def _contests(n, start_from=None):
        from datetime import datetime, timedelta
        base = start_from or datetime(2026, 6, 1, 19, 0)
        out = []
        for i in range(n):
            st = base + timedelta(days=i)
            out.append({
                "real_contest_id": 9000 + i, "name": f"NC Round {i}",
                "start_time": st.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": (st + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "duration_minutes": 120, "is_rated": True, "is_paid": False,
            })
        return out

    def test_truncation_keeps_newest(self):
        # 60 场 rated：截断到 50 场时必须保留最新的 50 场（9050..9099），
        # 被丢的应是最老的（9000..9049）——反向截断会让新比赛永远进不来。
        fake = _FakeNC(self._contests(60))
        with mock.patch.object(tasks_mod, "_load_scraper", return_value=fake):
            crawl_nowcoder(months=["2026-06", "2026-07"])
        ids = set(Contest.objects.filter(
            platform=Platform.NOWCODER).values_list("external_id", flat=True))
        self.assertEqual(len(ids), 50)
        self.assertIn("9059", ids)   # 最新一场
        self.assertIn("9010", ids)   # 第 50 新
        self.assertNotIn("9009", ids)
        self.assertNotIn("9000", ids)  # 最老 10 场被丢

    def test_unfinished_excluded(self):
        from datetime import timedelta
        from django.utils import timezone as dj_tz
        contests = self._contests(3)
        future = dj_tz.now() + timedelta(days=3)
        contests.append({
            "real_contest_id": 9999, "name": "NC Future Round",
            "start_time": future.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (future + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "duration_minutes": 120, "is_rated": True, "is_paid": False,
        })
        fake = _FakeNC(contests)
        with mock.patch.object(tasks_mod, "_load_scraper", return_value=fake):
            crawl_nowcoder(months=["2026-06", "2026-07"])
        ids = set(Contest.objects.filter(
            platform=Platform.NOWCODER).values_list("external_id", flat=True))
        self.assertNotIn("9999", ids)
        self.assertEqual(ids, {"9000", "9001", "9002"})


class NowcoderHistoryPruneTests(TestCase):
    """索引历史比赛不截断 + 已入库剪枝（2026-09 缺口修复：50 场截断线曾把
    最老的历史比赛永久挡住，新绑定用户的历史成绩永远补不上）。"""

    @staticmethod
    def _hist_contest(rid, day):
        from datetime import datetime, timedelta
        st = datetime(2025, 5, day, 19, 0)
        return {
            "real_contest_id": rid, "name": f"NC hist {rid}",
            "start_time": st.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (st + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "duration_minutes": 120, "is_rated": True, "is_paid": False,
        }

    @staticmethod
    def _rating_history(ids):
        # 全部落在 2025-05，反查只扩展这一个历史月份
        from datetime import datetime
        ts = datetime(2025, 5, 10).timestamp() * 1000
        return [{"contestId": str(i), "time": ts} for i in ids]

    def _bind_user(self, ids):
        user = User.objects.create_user(username="histu", password="pwd12345")
        return PlatformAccount.objects.create(
            user=user, platform=Platform.NOWCODER, handle="u1",
            participated_contests=[str(i) for i in ids])

    def test_history_beyond_50_still_crawled(self):
        # 60 场窗口外历史（索引指向、未入库）：不受 50 场截断，全部抓取入库
        ids = list(range(9000, 9060))
        contests = [self._hist_contest(i, 1 + (i % 28)) for i in ids]
        self._bind_user(ids)
        fake = _FakeNC(contests, {"u1": self._rating_history(ids)})
        with mock.patch.object(tasks_mod, "_load_scraper", return_value=fake):
            crawl_nowcoder(months=["2026-06"])
        self.assertEqual(
            Contest.objects.filter(platform=Platform.NOWCODER).count(), 60)

    def test_ingested_history_pruned_and_missing_replayed(self):
        from datetime import datetime, timedelta
        st = datetime(2026, 6, 1, 19, 0)
        contests = [
            self._hist_contest(9100, 10),
            self._hist_contest(9101, 20),
            self._hist_contest(9102, 25),
            {
                "real_contest_id": 9200, "name": "NC new",
                "start_time": st.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": (st + timedelta(hours=2)).strftime(
                    "%Y-%m-%d %H:%M:%S"),
                "duration_minutes": 120, "is_rated": True, "is_paid": False,
            },
        ]
        ids = [9100, 9101, 9102]
        acc = self._bind_user(ids)
        # 预入库 9101（绑定用户缺行）与 9102（绑定用户已有行）
        c9101 = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="9101", name="NC 9101")
        c9102 = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="9102", name="NC 9102")
        Participation.objects.create(
            contest=c9102, platform_account=acc,
            handle="u1", handle_lower="u1")
        self.assertIsNotNone(c9101)

        fake = _FakeNC(contests, {"u1": self._rating_history(ids)})
        with mock.patch.object(tasks_mod, "_load_scraper", return_value=fake):
            crawl_nowcoder(months=["2026-06"])
        # 9100 未入库 → 抓；9101 已入库缺行 → 重放补行；
        # 9102 已入库且行齐 → 剪掉；9200 窗口内新赛 → 照常抓
        self.assertEqual(set(fake.scraped), {"9100", "9101", "9200"})
        self.assertNotIn("9102", fake.scraped)


class CrawlConfigSignalTests(TestCase):
    """CrawlConfig 保存 → beat 调度条目同步。

    - 间隔 1 天：crontab 使用触发小时；
    - 间隔 >1 天：IntervalSchedule(every=N) 且 last_run_at 基准规整到
      00:00（Asia/Shanghai），实现「每 N 天 00:00 触发」；
    - enabled 同步到 PeriodicTask。
    """

    @staticmethod
    def _periodic():
        from django_celery_beat.models import PeriodicTask

        return PeriodicTask.objects.get(name="auto-crawl-daily")

    @staticmethod
    def _config():
        from apps.crawler.models import CrawlConfig

        cfg, _ = CrawlConfig.objects.get_or_create()
        return cfg

    def test_daily_uses_crontab_hour(self):
        cfg = self._config()
        cfg.auto_crawl_interval_days = 1
        cfg.auto_crawl_hour = 5
        cfg.save()
        pt = self._periodic()
        self.assertIsNotNone(pt.crontab)
        self.assertEqual(pt.crontab.hour, "5")
        self.assertIsNone(pt.interval)

    def test_multi_day_aligns_to_midnight(self):
        from django.utils import timezone as dj_tz

        cfg = self._config()
        cfg.auto_crawl_interval_days = 3
        cfg.enabled = True
        cfg.save()
        pt = self._periodic()
        self.assertIsNone(pt.crontab)
        self.assertEqual(pt.interval.every, 3)
        self.assertTrue(pt.enabled)
        # 基准规整到 00:00（Asia/Shanghai）——「每 3 天 00:00 触发」
        local = dj_tz.localtime(pt.last_run_at)
        self.assertEqual((local.hour, local.minute, local.second), (0, 0, 0))

        # enabled 关闭同步
        cfg.enabled = False
        cfg.save()
        pt.refresh_from_db()
        self.assertFalse(pt.enabled)


# ---------- 牛客历史缺失 / rating 涨落回填（2026-09-22 学生榜第一名案例）----------

import tempfile  # noqa: E402
from datetime import datetime, timedelta, timezone as dt_tz  # noqa: E402
from pathlib import Path  # noqa: E402

from django.conf import settings  # noqa: E402
from django.test import override_settings  # noqa: E402
from django.utils import timezone as dj_tz  # noqa: E402

from apps.crawler import ingest as ingest_mod  # noqa: E402
from apps.crawler.ingest import (backfill_account_history,  # noqa: E402
                                 missing_nowcoder_contest_ids)
from apps.crawler.tasks import (_contest_cache_ttl,  # noqa: E402
                               reap_stale_crawl_jobs, sweep_nowcoder_history)


def _dt_str(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _nc_contest(rid, days_ago):
    st = dj_tz.now() - timedelta(days=days_ago)
    return {
        "real_contest_id": rid, "name": f"NC {rid}",
        "start_time": _dt_str(st),
        "end_time": _dt_str(st + timedelta(hours=2)),
        "duration_minutes": 120, "is_rated": True, "is_paid": False,
    }


def _nc_detail(uid="1001", rank=7, score=300.0):
    return {
        "problems": [],
        "ranks": [{
            "rank": rank, "uid": int(uid), "user_name": "不知名小帅",
            "school": None, "team": False, "accepted_count": 4,
            "total_score": score, "full_score": 600.0, "penalty_time_ms": 0,
            "color_level": 3, "post_contest_append": False,
            "is_cheater": False, "score_detail": [], "extra": {},
        }],
        "rank_count": 1, "valid_rank_count": 1, "crawled_at": "2026-09-22T00:00:00",
    }


class _FakeHistoryScraper:
    """只实现 backfill_account_history 用到的接口面，全程不联网。"""

    def __init__(self, detail=None, rated_ids=(), info=None):
        self.detail = detail or _nc_detail()
        self.rated_ids = {str(i) for i in rated_ids}
        self._info = info or {}
        self.scraped = []      # (external_id, cache_ttl_hours)
        self.info_calls = []

    def init_session(self):
        pass

    def fetch_contest_info(self, rid, use_cache=True):
        self.info_calls.append(str(rid))
        return self._info.get(str(rid))

    def check_rated(self, meta):
        rid = str(meta.get("real_contest_id"))
        return {"is_rated": rid in self.rated_ids,
                "rated_comment": "fake", "name": f"NC {rid}"}

    @staticmethod
    def _ts2str(ts):
        if not ts:
            return None
        return datetime.fromtimestamp(int(ts) / 1000, tz=dt_tz.utc) \
            .strftime("%Y-%m-%d %H:%M:%S")

    def scrape_contest_detail(self, rid, filter_post_contest=False,
                              exclude_cheaters=False, cache_dir=None,
                              cache_ttl_hours=168, **kwargs):
        self.scraped.append((str(rid), cache_ttl_hours))
        return self.detail


class ContestCacheTtlTests(TestCase):
    """已结束足够久的比赛：榜单原文已冻结，落盘缓存不该再判过期。"""

    @staticmethod
    def _meta(days_ago):
        return {"end_time": _dt_str(dj_tz.now() - timedelta(days=days_ago))}

    def test_old_contest_cache_never_expires(self):
        # 阈值取 7 天：结束满 7 天即视为不可变
        self.assertIsNone(_contest_cache_ttl(self._meta(8)))
        self.assertIsNone(_contest_cache_ttl(self._meta(60)))

    def test_recent_contest_keeps_ttl(self):
        self.assertEqual(_contest_cache_ttl(self._meta(6)),
                         settings.CRAWLER_CACHE_TTL_HOURS)
        self.assertEqual(_contest_cache_ttl(self._meta(2)),
                         settings.CRAWLER_CACHE_TTL_HOURS)

    def test_unparsable_end_time_falls_back_to_ttl(self):
        self.assertEqual(_contest_cache_ttl({"name": "没有时间字段"}),
                         settings.CRAWLER_CACHE_TTL_HOURS)

    @override_settings(CRAWLER_IMMUTABLE_AFTER_DAYS=0)
    def test_policy_can_be_switched_off(self):
        self.assertEqual(_contest_cache_ttl(self._meta(600)),
                         settings.CRAWLER_CACHE_TTL_HOURS)


class NowcoderCrawlTtlTests(TestCase):
    """爬取调用侧按场次新旧下发不同 TTL —— 历史场次必须靠本地缓存重放。"""

    def test_old_contest_scraped_with_infinite_ttl(self):
        old, fresh = _nc_contest(9001, 60), _nc_contest(9002, 2)
        months = sorted({old["start_time"][:7], fresh["start_time"][:7]})
        fake = _FakeNC([old, fresh])
        with mock.patch.object(tasks_mod, "_load_scraper", return_value=fake):
            crawl_nowcoder(months=months)
        ttl_by_id = dict(fake.ttl_calls)
        self.assertEqual(ttl_by_id.get("9001"), None)
        self.assertEqual(ttl_by_id.get("9002"), settings.CRAWLER_CACHE_TTL_HOURS)


class NowcoderBackfillDispatchTests(TestCase):
    """爬取被打断时牛客 rating 涨落回填必须照跑。

    回归缺陷：回填原先写在爬取生成器 `for … yield` 之后，任务被
    SoftTimeLimitExceeded 打断时生成器直接作废、尾部一行都不执行（实测
    09-21/09-22 两轮皆如此），结果是那之后所有新入库的牛客成绩都没有涨落，
    个人页「各平台官方 Rating」卡片整块消失。
    """

    class _BoomNC:
        """第一场抓成功、第二场抛软超时 —— 与生产 job #130/#131 的形态一致。"""

        def __init__(self, contests):
            self._contests = contests
            self.scraped = []

        def init_session(self):
            pass

        def fetch_contests(self, ym):
            return [c for c in self._contests if c["start_time"][:7] == ym]

        def parse_contests(self, lst, only_nowcoder=True):
            return lst

        def filter_contests(self, contests, rated_only=True, exclude_paid=True):
            return [c for c in contests if c.get("is_rated")]

        def scrape_contest_detail(self, rid, **kwargs):
            from billiard.exceptions import SoftTimeLimitExceeded
            self.scraped.append(str(rid))
            if len(self.scraped) > 1:
                raise SoftTimeLimitExceeded()
            return {"problems": [], "ranks": [], "rank_count": 0,
                    "valid_rank_count": 0, "crawled_at": "2026-09-22T00:00:00"}

    @staticmethod
    def _months_of(*contests):
        return sorted({c["start_time"][:7] for c in contests})

    def _run(self, fake, months):
        with mock.patch.object(tasks_mod, "_load_scraper", return_value=fake), \
                mock.patch.object(tasks_mod, "_broker_reachable", return_value=True), \
                mock.patch("apps.ranking.tasks.recompute_ranking_task"), \
                mock.patch.object(tasks_mod, "backfill_nowcoder_ratings_task") as bf:
            crawl_nowcoder(months=months)
        return bf

    def test_soft_timeout_still_dispatches_rating_backfill(self):
        c1, c2 = _nc_contest(9001, 100), _nc_contest(9002, 90)
        bf = self._run(self._BoomNC([c1, c2]), self._months_of(c1, c2))
        job = CrawlJob.objects.filter(platform=Platform.NOWCODER).latest("id")
        # 入库了一半就被打断：旧实现里回填写在生成器尾部，这一步会整段跳过
        self.assertEqual(job.status, CrawlJob.Status.PARTIAL)
        self.assertEqual(job.contest_count, 1)
        bf.delay.assert_called_once()

    def test_success_also_dispatches_rating_backfill(self):
        c1 = _nc_contest(9001, 100)
        bf = self._run(_FakeNC([c1]), self._months_of(c1))
        job = CrawlJob.objects.filter(platform=Platform.NOWCODER).latest("id")
        self.assertEqual(job.status, CrawlJob.Status.SUCCESS)
        bf.delay.assert_called_once()


class MissingNowcoderContestIdsTests(TestCase):
    """缺口口径 = 「该账号缺这一行」，比赛早已入库同样算缺。

    旧补抓命令按「比赛未入库」筛选，所以「已入库但缺新绑定用户行」这类
    缺口（2026-09-22 实测：21 场缺失里 20 场属于此类）永远修不掉。
    """

    def setUp(self):
        user = User.objects.create_user(username="mstu", password="pwd12345")
        self.acc = PlatformAccount.objects.create(
            user=user, platform=Platform.NOWCODER, handle="1001",
            participated_contests=["9001", "9002", "9003"])
        c9001 = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="9001", name="NC 9001",
            is_rated=True)
        Contest.objects.create(platform=Platform.NOWCODER, external_id="9002",
                               name="NC 9002", is_rated=True)
        Participation.objects.create(contest=c9001, platform_account=self.acc,
                                     handle="1001")

    def test_missing_covers_ingested_contest_without_row(self):
        self.assertEqual(missing_nowcoder_contest_ids(self.acc),
                         {"9002", "9003"})

    def test_complete_account_has_no_gap(self):
        """索引里的场次都有行 → 无缺口（9002/9003 不在索引里就不该被算作缺）。"""
        self.acc.participated_contests = ["9001"]
        self.acc.save()
        self.assertEqual(missing_nowcoder_contest_ids(self.acc), set())


class BackfillAccountHistoryTests(TestCase):
    """定向补数：按账号补齐历史行，非牛客账号拒绝，dry-run 零写入。"""

    def setUp(self):
        user = User.objects.create_user(username="bfu", password="pwd12345")
        self.acc = PlatformAccount.objects.create(
            user=user, platform=Platform.NOWCODER, handle="1001")
        self.contest = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="9001", name="NC 9001",
            is_rated=True, start_time=dj_tz.now() - timedelta(days=200),
            end_time=dj_tz.now() - timedelta(days=200) + timedelta(hours=2),
            raw_meta={"origin": "原样保留"})

    def test_creates_missing_row_for_ingested_contest(self):
        self.acc.participated_contests = ["9001"]
        self.acc.save()
        fake = _FakeHistoryScraper()
        with mock.patch.object(ingest_mod, "backfill_nowcoder_ratings",
                               return_value={"updated": 1}) as rb:
            stats = backfill_account_history(self.acc, scraper=fake)
        self.assertEqual(stats["ingested"], 1)
        row = Participation.objects.get(contest=self.contest,
                                        platform_account=self.acc)
        self.assertEqual(row.rank, 7)
        self.assertEqual(row.total_score, 300.0)
        # 200 天前结束 → 缓存不失效，重放不再下载整场榜单
        self.assertEqual(fake.scraped, [("9001", None)])
        # 补完行必须接着回填涨落，否则折线图依然空
        rb.assert_called_once_with(account_ids=[self.acc.pk])
        self.contest.refresh_from_db()
        self.assertEqual(self.contest.raw_meta["origin"], "原样保留")

    def test_prefers_contests_with_local_cache(self):
        # 9002 比 9001 新，但 9001 的榜单原文已在本地 → 零网络的必须先做，
        # 这样在固定的时间预算内能补完更多场次
        Contest.objects.create(platform=Platform.NOWCODER, external_id="9002",
                               name="NC 9002", is_rated=True)
        self.acc.participated_contests = ["9001", "9002"]
        self.acc.save()
        fake = _FakeHistoryScraper()
        with tempfile.TemporaryDirectory() as tmp:
            # 缓存按平台分子目录：crawlers/data/<platform>/contest_<id>.json
            nc_dir = Path(tmp) / Platform.NOWCODER
            nc_dir.mkdir()
            (nc_dir / "contest_9001.json").write_text("{}", encoding="utf-8")
            with override_settings(CRAWLER_CACHE_DIR=tmp), \
                    mock.patch.object(ingest_mod, "backfill_nowcoder_ratings",
                                      return_value={"updated": 0}):
                backfill_account_history(self.acc, scraper=fake)
        self.assertEqual([rid for rid, _ in fake.scraped], ["9001", "9002"])

    def test_dry_run_writes_nothing(self):
        self.acc.participated_contests = ["9001"]
        self.acc.save()
        with mock.patch.object(ingest_mod, "backfill_nowcoder_ratings") as rb:
            stats = backfill_account_history(self.acc, scraper=_FakeHistoryScraper(),
                                             dry_run=True)
        self.assertEqual(stats["pending"], 1)
        self.assertEqual(stats["ingested"], 0)
        self.assertFalse(Participation.objects.exists())
        rb.assert_not_called()

    def test_non_rated_unknown_contest_skipped(self):
        self.acc.participated_contests = ["8888"]
        self.acc.save()
        fake = _FakeHistoryScraper(rated_ids=(), info={
            "8888": {"name": "NC 8888", "startTime": None, "endTime": None}})
        with mock.patch.object(ingest_mod, "backfill_nowcoder_ratings",
                               return_value={"updated": 0}):
            stats = backfill_account_history(self.acc, scraper=fake)
        self.assertEqual(stats["skipped"], 1)
        self.assertFalse(Contest.objects.filter(external_id="8888").exists())
        self.assertEqual(fake.scraped, [])

    def test_new_rated_contest_created_and_ingested(self):
        self.acc.participated_contests = ["8888"]
        self.acc.save()
        ts = int((dj_tz.now() - timedelta(days=40)).timestamp() * 1000)
        fake = _FakeHistoryScraper(rated_ids=["8888"], info={
            "8888": {"name": "NC 8888", "startTime": ts,
                     "endTime": ts + 7200000}})
        with mock.patch.object(ingest_mod, "backfill_nowcoder_ratings",
                               return_value={"updated": 0}):
            stats = backfill_account_history(self.acc, scraper=fake)
        self.assertEqual(stats["ingested"], 1)
        new = Contest.objects.get(external_id="8888")
        self.assertTrue(new.is_rated)
        self.assertEqual(new.duration_minutes, 120)
        self.assertEqual(fake.scraped, [("8888", None)])

    def test_refuses_non_nowcoder_account(self):
        user = User.objects.create_user(username="bfu2", password="pwd12345")
        cf = PlatformAccount.objects.create(user=user, platform=Platform.CODEFORCES,
                                            handle="alice")
        with self.assertRaises(ValueError):
            backfill_account_history(cf, scraper=_FakeHistoryScraper())


class SweepNowcoderHistoryTests(TestCase):
    """每日巡检兜底：只处理确有缺口的账号，索引为空的先补索引，预算生效。"""

    def _account(self, username, handle, index):
        user = User.objects.create_user(username=username, password="pwd12345")
        return PlatformAccount.objects.create(
            user=user, platform=Platform.NOWCODER, handle=handle,
            participated_contests=index)

    def test_only_gap_accounts_processed_and_budget_respected(self):
        cold = self._account("cold", "2001", [])          # 索引为空
        gap = self._account("gap", "1001", ["9001"])      # 有缺口
        Contest.objects.create(platform=Platform.NOWCODER, external_id="9001",
                               name="NC 9001", is_rated=True)
        with mock.patch.object(ingest_mod, "fill_participated_contests",
                               return_value=(False, 0)) as fill, \
                mock.patch.object(ingest_mod, "backfill_account_history",
                                  return_value={"pending": 1, "ingested": 1,
                                                "skipped": 0, "failed": 0}) as bf, \
                mock.patch.object(tasks_mod, "_broker_reachable",
                                  return_value=False):
            res = sweep_nowcoder_history(max_accounts=5)
        fill.assert_called_once()
        self.assertEqual(fill.call_args[0][0].pk, cold.pk)
        self.assertEqual([c[0][0].pk for c in bf.call_args_list], [gap.pk])
        self.assertEqual(res["accounts"][0]["account"], gap.pk)

    def test_budget_limits_accounts_per_run(self):
        for i in range(3):
            self._account(f"u{i}", f"100{i}", ["9001"])
        Contest.objects.create(platform=Platform.NOWCODER, external_id="9001",
                               name="NC 9001", is_rated=True)
        with mock.patch.object(ingest_mod, "backfill_account_history",
                               return_value={"pending": 1, "ingested": 0,
                                             "skipped": 0, "failed": 0}) as bf, \
                mock.patch.object(tasks_mod, "_broker_reachable",
                                  return_value=False):
            sweep_nowcoder_history(max_accounts=2)
        self.assertEqual(bf.call_count, 2)

    def test_no_recompute_when_nothing_ingested(self):
        """补不动的缺口（rated 口径差异）不该每天触发一次全站重算。"""
        acc = self._account("gap2", "1009", ["9001"])
        Contest.objects.create(platform=Platform.NOWCODER, external_id="9001",
                               name="NC 9001", is_rated=True)
        with mock.patch.object(ingest_mod, "backfill_account_history",
                               return_value={"pending": 1, "ingested": 0,
                                             "skipped": 1, "failed": 0}), \
                mock.patch.object(tasks_mod, "_broker_reachable",
                                  return_value=True), \
                mock.patch("apps.ranking.tasks.recompute_ranking_task") as rc:
            res = sweep_nowcoder_history(max_accounts=5)
        rc.delay.assert_not_called()
        self.assertEqual(res["still_pending"], [{"account": acc.pk, "pending": 1}])


class ReapStaleCrawlJobsTests(TestCase):
    """worker 被重启打断的爬取任务会永久停在 running，巡检要把它们判死。"""

    def test_stale_running_marked_failed_recent_untouched(self):
        stale = CrawlJob.objects.create(platform=Platform.NOWCODER,
                                        status=CrawlJob.Status.RUNNING)
        CrawlJob.objects.filter(pk=stale.pk).update(
            updated_at=dj_tz.now() - timedelta(hours=5))
        live = CrawlJob.objects.create(platform=Platform.CODEFORCES,
                                       status=CrawlJob.Status.RUNNING)
        self.assertEqual(reap_stale_crawl_jobs(), [stale.pk])
        stale.refresh_from_db()
        live.refresh_from_db()
        self.assertEqual(stale.status, CrawlJob.Status.FAILED)
        self.assertIsNotNone(stale.finished_at)
        self.assertIn("状态收割", stale.error_message)
        self.assertEqual(live.status, CrawlJob.Status.RUNNING)
