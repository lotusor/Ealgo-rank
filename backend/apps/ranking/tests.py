"""#5 积分排名引擎单元测试。"""
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import PlatformAccount, User, UserRole
from apps.common.models import Platform
from apps.contests.models import Contest, Participation
from apps.ranking.engine import (
    compute_base_score,
    recompute_all,
    recompute_score_records,
    recompute_snapshots,
)
from apps.ranking.models import RankSnapshot, ScoreRecord
from apps.schools.models import ScoreConfig, School


def make_config(recent_limit=0):
    """全局唯一积分配置（超管统一设置，不分学校）。"""
    return ScoreConfig.objects.create(
        cf_factor=1.0, atcoder_factor=1.0, nowcoder_factor=0.8,
        default_contest_factor=1.0, platform_weight=0.5,
        contest_weight=0.5, recent_contest_limit=recent_limit)


class EngineTests(TestCase):
    def setUp(self):
        make_config(recent_limit=1)  # 全局统一配置：个人榜每平台最近 1 场
        self.school_a = School.objects.create(name="A大学", code="a")
        self.school_b = School.objects.create(name="B大学", code="b")

        self.ua = User.objects.create_user(username="ua", school=self.school_a)
        self.ub = User.objects.create_user(username="ub", school=self.school_a)
        self.uc = User.objects.create_user(username="uc", school=self.school_b)

        self.pa_cf_a = PlatformAccount.objects.create(
            user=self.ua, platform=Platform.CODEFORCES, handle="cfa",
            handle_lower="cfa", school=self.school_a)
        self.pa_nc_a = PlatformAccount.objects.create(
            user=self.ua, platform=Platform.NOWCODER, handle="nca",
            handle_lower="nca", school=self.school_a)
        self.pa_cf_b = PlatformAccount.objects.create(
            user=self.ub, platform=Platform.CODEFORCES, handle="cfb",
            handle_lower="cfb", school=self.school_a)
        self.pa_cf_c = PlatformAccount.objects.create(
            user=self.uc, platform=Platform.CODEFORCES, handle="cfc",
            handle_lower="cfc", school=self.school_b)

        # 三场比赛（均 2026，rated，非付费）
        self.c1 = Contest.objects.create(
            platform=Platform.CODEFORCES, external_id="c1",
            name="CF1", start_time="2026-01-01T00:00:00Z",
            is_rated=True, is_paid=False, valid_participant_count=100,
            difficulty_factor=1.5)
        self.c2 = Contest.objects.create(
            platform=Platform.CODEFORCES, external_id="c2",
            name="CF2", start_time="2026-02-01T00:00:00Z",
            is_rated=True, is_paid=False, valid_participant_count=100,
            difficulty_factor=1.0)  # 1.0 -> 回退学校默认
        self.c3 = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="c3",
            name="NC1", start_time="2026-03-01T00:00:00Z",
            is_rated=True, is_paid=False, valid_participant_count=50,
            difficulty_factor=1.2)

        # 可计分的参赛记录
        Participation.objects.create(contest=self.c1, platform_account=self.pa_cf_a,
                                     handle="cfa", handle_lower="cfa", rank=1)
        Participation.objects.create(contest=self.c2, platform_account=self.pa_cf_a,
                                     handle="cfa", handle_lower="cfa", rank=51)
        Participation.objects.create(contest=self.c3, platform_account=self.pa_nc_a,
                                     handle="nca", handle_lower="nca", rank=5)
        Participation.objects.create(contest=self.c1, platform_account=self.pa_cf_b,
                                     handle="cfb", handle_lower="cfb", rank=10)
        Participation.objects.create(contest=self.c1, platform_account=self.pa_cf_c,
                                     handle="cfc", handle_lower="cfc", rank=2)
        # 一条被排除的（不同 handle），不应参与计分
        Participation.objects.create(contest=self.c1, platform_account=self.pa_cf_a,
                                     handle="cfcheat", handle_lower="cfcheat",
                                     rank=3, is_excluded=True,
                                     exclude_reason="cheater")

    # ---------- 基础分 ----------
    def test_base_score_normalization(self):
        p = Participation.objects.get(contest=self.c1,
                                      platform_account=self.pa_cf_a,
                                      handle_lower="cfa")
        self.assertAlmostEqual(compute_base_score(p), 100.0)  # rank 1 / 100
        p2 = Participation.objects.get(contest=self.c1,
                                       platform_account=self.pa_cf_b,
                                       handle_lower="cfb")
        self.assertAlmostEqual(compute_base_score(p2), 91.0)  # rank 10

    # ---------- ScoreRecord 算分 ----------
    def test_score_records_computed(self):
        res = recompute_score_records()
        self.assertEqual(ScoreRecord.objects.count(), 5)  # 排除的那条不计
        # ua 在 c1(cf,难度1.5): base=100, combined=0.5*1+0.5*1.5=1.25 -> 125
        sr = ScoreRecord.objects.get(participation__contest=self.c1,
                                     platform_account=self.pa_cf_a)
        self.assertAlmostEqual(sr.base_score, 100.0)
        self.assertAlmostEqual(sr.final_score, 125.0)
        # ua 在 c2(cf,难度1.0回退默认1.0): base=50, combined=1.0 -> 50
        sr2 = ScoreRecord.objects.get(participation__contest=self.c2,
                                      platform_account=self.pa_cf_a)
        self.assertAlmostEqual(sr2.final_score, 50.0)

    # ---------- 学校榜聚合（汇总全部，不限场次） ----------
    def test_school_snapshot(self):
        recompute_score_records()
        n = recompute_snapshots(RankSnapshot.Scope.SCHOOL, "all")
        self.assertEqual(n, 2)  # 两所学校
        a = RankSnapshot.objects.get(scope="school", period="all",
                                     school=self.school_a)
        # ua: 125+50+92(nc) = 267 ; ub: 113.75 -> 380.75
        self.assertAlmostEqual(float(a.total_score), 380.75)
        self.assertEqual(a.member_count, 2)
        self.assertEqual(a.contest_count, 4)
        b = RankSnapshot.objects.get(scope="school", period="all",
                                     school=self.school_b)
        self.assertAlmostEqual(float(b.total_score), 123.75)
        self.assertEqual(a.rank, 1)
        self.assertEqual(b.rank, 2)

    # ---------- 个人榜（每平台最近 1 场） ----------
    def test_student_snapshot_recent_limit(self):
        recompute_score_records()
        n = recompute_snapshots(RankSnapshot.Scope.STUDENT, "all")
        self.assertEqual(n, 3)
        ua = RankSnapshot.objects.get(scope="student", period="all",
                                      user=self.ua)
        # 全局 limit=1：每平台取最新一场。cf 最新为 c2(50)，nc 为 c3(92) -> 142
        self.assertAlmostEqual(float(ua.total_score), 142.0)
        self.assertEqual(ua.contest_count, 2)
        ub = RankSnapshot.objects.get(scope="student", period="all",
                                      user=self.ub)
        self.assertAlmostEqual(float(ub.total_score), 113.75)
        uc = RankSnapshot.objects.get(scope="student", period="all",
                                      user=self.uc)
        self.assertAlmostEqual(float(uc.total_score), 123.75)
        # 名次：ua(217) > uc(123.75) > ub(113.75)
        self.assertEqual(ua.rank, 1)
        self.assertEqual(uc.rank, 2)
        self.assertEqual(ub.rank, 3)

    # ---------- 周期过滤 ----------
    def test_period_filter_current_year(self):
        recompute_score_records()
        n = recompute_snapshots(RankSnapshot.Scope.STUDENT, "2026")
        self.assertEqual(n, 3)  # 均在 2026
        n2 = recompute_snapshots(RankSnapshot.Scope.STUDENT, "2025")
        self.assertEqual(n2, 0)  # 无 2025 数据

    # ---------- 全量入口 ----------
    def test_recompute_all(self):
        res = recompute_all()
        self.assertIn("snapshots", res)
        # all + 2026 两个周期 × 2 scope = 4 个快照组
        self.assertEqual(len(res["snapshots"]), 4)

    # ---------- API 只读 + 重算动作 ----------
    def test_ranking_api_list(self):
        from rest_framework.test import APIClient
        recompute_all()
        client = APIClient()
        resp = client.get("/api/v1/rankings/",
                          {"scope": "school", "period": "all"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 2)

    def test_recompute_action_requires_super(self):
        from rest_framework.test import APIClient
        from apps.accounts.models import User as AUser, UserRole
        client = APIClient()
        # 普通用户无权限
        normal = AUser.objects.create_user(username="normal")
        client.force_authenticate(normal)
        r = client.post("/api/v1/rankings/recompute/")
        self.assertEqual(r.status_code, 403)
        # 超管可触发
        sup = AUser.objects.create_user(username="sup",
                                         role=UserRole.SUPER_ADMIN)
        client.force_authenticate(sup)
        r = client.post("/api/v1/rankings/recompute/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(RankSnapshot.objects.exists())
