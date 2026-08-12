"""
入库层测试，重点覆盖作弊账号排除 —— 这条一旦漏掉会直接污染学校积分。
"""

from django.test import TestCase

from apps.accounts.models import PlatformAccount, User
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
