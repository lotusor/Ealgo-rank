"""#5 积分排名引擎 v3（统一表现分）单元测试。

覆盖：表现分 z 数学 / 难度基线查找链 / 先验新号机制 / 滑动窗口 /
学校与学生榜聚合 / 并列名次 / 周期过滤 / 付费场计分 / rating-history API。
"""
from statistics import NormalDist

from django.test import TestCase

from apps.accounts.models import PlatformAccount, User, UserRole
from apps.common.models import Platform
from apps.contests.models import Contest, ContestDifficultyFactor, Participation
from apps.ranking.engine import (
    compute_performance,
    contest_perf_base,
    rank_z,
    rating_history,
    recompute_all,
    recompute_score_records,
    recompute_snapshots,
    update_user_best_records,
)
from apps.ranking.models import RankSnapshot, ScoreRecord, UserBestRecord
from apps.schools.models import ScoreConfig, School


def make_config(recent_limit=0, decay=1.0, prior=1200.0):
    """全局唯一积分配置（超管统一设置，不分学校）。"""
    return ScoreConfig.objects.create(
        cf_factor=1.0, atcoder_factor=1.0, nowcoder_factor=1.0,
        default_contest_factor=1.0, platform_weight=0.5,
        contest_weight=0.5, recent_contest_limit=recent_limit,
        rating_decay=decay, rating_prior=prior)


_NORM = NormalDist()


class PerfMathTests(TestCase):
    """表现分：名次百分位 → z → perf 的换算与边界。"""

    def setUp(self):
        make_config()  # 全 1.0 系数
        self.school = School.objects.create(name="M大学", code="m")
        self.u = User.objects.create_user(username="mu", school=self.school)
        self.pa = PlatformAccount.objects.create(
            user=self.u, platform=Platform.CODEFORCES, handle="mcf",
            handle_lower="mcf", school=self.school)

    def _participation(self, rank, vp, series="Div. 2", platform=Platform.CODEFORCES):
        from datetime import datetime, timedelta
        from django.utils import timezone as tz
        n = Participation.objects.filter(contest__platform=platform).count()
        c = Contest.objects.create(
            platform=platform, external_id=f"mp{n}",
            name=f"MP {series} {n}", series=series,
            start_time=tz.make_aware(datetime(2026, 1, 1) + timedelta(days=n)),
            is_rated=True, is_paid=False, participant_count=vp)
        return Participation.objects.create(
            contest=c, platform_account=self.pa, handle="mcf",
            handle_lower="mcf", rank=rank)

    def test_rank_z(self):
        # 中位：rank 501/1000 → z≈0
        self.assertAlmostEqual(rank_z(501, 1000), 0.0, places=2)
        # 榜首大场：z 很大
        self.assertGreater(rank_z(1, 1000), 3.2)
        # 垫底：z 很小
        self.assertLess(rank_z(1000, 1000), -3.2)
        # 无信息：缺 rank / 单人场 → 0
        self.assertEqual(rank_z(None, 100), 0.0)
        self.assertEqual(rank_z(1, 1), 0.0)
        self.assertEqual(rank_z(0, 100), 0.0)

    def test_median_perf_equals_base(self):
        # 名次中位 → z≈0 → perf≈D（Div. 2 = 1450）
        p = self._participation(500, 999)
        perf, z, base, pf = compute_performance(p, ScoreConfig.get_config())
        self.assertEqual(base, 1450.0)
        self.assertAlmostEqual(z, 0.0, places=2)
        self.assertAlmostEqual(perf, 1450.0, delta=1.0)

    def test_top_rank_above_base(self):
        p = self._participation(1, 1000)
        perf, z, base, pf = compute_performance(p, ScoreConfig.get_config())
        # z = Φ⁻¹(1 - 0.5/1000) ≈ 3.29 → 1450 + 400*3.29 ≈ 2766
        self.assertAlmostEqual(perf, 1450 + 400 * _NORM.inv_cdf(0.9995), places=1)

    def test_perf_clamped(self):
        # 超管覆盖位把 D 抬到 9900，clamp 拦住
        ContestDifficultyFactor.objects.update_or_create(
            platform=Platform.CODEFORCES, series="Div. 2",
            defaults={"perf_base": 9900.0})
        p = self._participation(500, 999)
        perf, _, _, _ = compute_performance(p, ScoreConfig.get_config())
        self.assertEqual(perf, 4000.0)  # PERF_MAX

    def test_perf_base_lookup_chain(self):
        # ① 超管覆盖位优先
        ContestDifficultyFactor.objects.update_or_create(
            platform=Platform.CODEFORCES, series="Div. 2",
            defaults={"perf_base": 2000.0})
        c = Contest.objects.create(
            platform=Platform.CODEFORCES, external_id="bc1", name="BC",
            series="Div. 2", start_time="2026-01-01T00:00:00Z",
            is_rated=True, is_paid=False)
        self.assertEqual(contest_perf_base(c), 2000.0)
        # ② 精确系列默认表
        c2 = Contest.objects.create(
            platform=Platform.CODEFORCES, external_id="bc2", name="BC2",
            series="Div. 3", start_time="2026-01-02T00:00:00Z",
            is_rated=True, is_paid=False)
        self.assertEqual(contest_perf_base(c2), 1150.0)
        # ③ 平台默认（未知系列）
        c3 = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="bc3", name="BC3",
            series="神秘系列", start_time="2026-01-03T00:00:00Z",
            is_rated=True, is_paid=False)
        self.assertEqual(contest_perf_base(c3), 1000.0)
        # ④ 无系列
        c4 = Contest.objects.create(
            platform=Platform.ATCODER, external_id="bc4", name="BC4",
            start_time="2026-01-04T00:00:00Z",
            is_rated=True, is_paid=False)
        self.assertEqual(contest_perf_base(c4), 900.0)


class SiteRatingTests(TestCase):
    """站点 rating：先验新号机制 + 滑动窗口。"""

    def setUp(self):
        make_config(recent_limit=3, decay=0.5, prior=1000.0)
        self.school = School.objects.create(name="S大学", code="s")
        self.u = User.objects.create_user(username="su", school=self.school)
        self.pa = PlatformAccount.objects.create(
            user=self.u, platform=Platform.CODEFORCES, handle="scf",
            handle_lower="scf", school=self.school)

    def _seed(self, perfs, platform=Platform.CODEFORCES, prefix="sc"):
        """按时间升序造 countable 记录，用 perf_base 把 perf 钉在给定值上。

        z 取 0（单人场），perf = pf × D → 直接控制 D 控制表现分。
        """
        from datetime import datetime, timedelta
        from django.utils import timezone as tz
        base = tz.make_aware(datetime(2026, 1, 1))
        for i, perf in enumerate(perfs):
            ContestDifficultyFactor.objects.update_or_create(
                platform=platform, series=f"S{i}",
                defaults={"perf_base": perf})
            c = Contest.objects.create(
                platform=platform, external_id=f"{prefix}{i}",
                name=f"SC {i}", series=f"S{i}",
                start_time=base + timedelta(days=i),
                is_rated=True, is_paid=False, participant_count=1)
            Participation.objects.create(
                contest=c, platform_account=self.pa, handle="scf",
                handle_lower="scf", rank=1)

    def _student_total(self):
        recompute_score_records()
        recompute_snapshots(RankSnapshot.Scope.STUDENT, "all")
        snap = RankSnapshot.objects.get(scope="student", period="all",
                                        user=self.u)
        return float(snap.total_score)

    def test_prior_blends_first_contest(self):
        # 首场 perf=2000，先验 1000，decay 0.5：
        # (2000×1 + 1000×0.5) / (1+0.5) = 2500/1.5 ≈ 1666.67
        self._seed([2000.0])
        self.assertAlmostEqual(self._student_total(), 2500.0 / 1.5, places=3)

    def test_prior_fades_with_contests(self):
        # 两场 [2000, 2000]（旧→新），decay 0.5：
        # (2000 + 2000×0.5 + 1000×0.25) / (1+0.5+0.25) = 3250/1.75 ≈ 1857.14
        # （先验权重 0.25，同场越多越趋近真实水平 2000）
        self._seed([2000.0, 2000.0])
        self.assertAlmostEqual(self._student_total(), 3250.0 / 1.75, places=3)

    def test_window_respects_n_and_decay(self):
        # N=3：四场 [100, 200, 400, 800]（旧→新），窗口取最新 3 场 [800,400,200]
        # (800 + 400×0.5 + 200×0.25 + 1000×0.125)/(1+0.5+0.25+0.125)
        # = 1175/1.875 ≈ 626.67
        self._seed([100.0, 200.0, 400.0, 800.0])
        self.assertAlmostEqual(self._student_total(), 1175.0 / 1.875, places=3)

    def test_crash_softened_by_window(self):
        # 核心价值：一场暴跌（900→300）不再直接钉死 rating
        # 窗口 [300, 900, 900]：(300 + 450 + 225 + 125)/1.875 ≈ 586.67
        self._seed([900.0, 900.0, 300.0])
        self.assertAlmostEqual(self._student_total(), 1100.0 / 1.875, places=3)

    def test_new_account_strong_performance_wins(self):
        # 新号机制：平台 rating 不参与，同场不同名次 → 表现分立见高下
        u2 = User.objects.create_user(username="sv", school=self.school)
        pa2 = PlatformAccount.objects.create(
            user=u2, platform=Platform.CODEFORCES, handle="scf2",
            handle_lower="scf2", school=self.school)
        ContestDifficultyFactor.objects.update_or_create(
            platform=Platform.CODEFORCES, series="W",
            defaults={"perf_base": 1450.0})
        c = Contest.objects.create(
            platform=Platform.CODEFORCES, external_id="w1", name="W1",
            series="W", start_time="2026-01-01T00:00:00Z",
            is_rated=True, is_paid=False, participant_count=1001)
        # ua 的新手号（new_rating 极低）但名次第 2；u2 rating 很高但名次 500
        Participation.objects.create(
            contest=c, platform_account=self.pa, handle="scf",
            handle_lower="scf", rank=2, new_rating=800.0)
        Participation.objects.create(
            contest=c, platform_account=pa2, handle="scf2",
            handle_lower="scf2", rank=500, new_rating=2600.0)
        recompute_score_records()
        p1 = ScoreRecord.objects.get(platform_account=self.pa).final_score
        p2 = ScoreRecord.objects.get(platform_account=pa2).final_score
        # 平台 rating 完全不参与：第 2 名表现分远高于第 500 名
        self.assertGreater(p1, p2 + 500)


class SnapshotTests(TestCase):
    """榜单聚合：学校/学生榜、并列名次、周期、付费场、全量入口。"""

    def setUp(self):
        make_config(recent_limit=1, decay=0.0, prior=0.0)
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

        # 两场 CF Div.2（D=1450）+ 一场牛客周赛（D=950），vp=1000
        self.c1 = Contest.objects.create(
            platform=Platform.CODEFORCES, external_id="c1", name="CF1",
            series="Div. 2", start_time="2026-01-01T00:00:00Z",
            is_rated=True, is_paid=False, participant_count=1000)
        self.c2 = Contest.objects.create(
            platform=Platform.CODEFORCES, external_id="c2", name="CF2",
            series="Div. 2", start_time="2026-02-01T00:00:00Z",
            is_rated=True, is_paid=False, participant_count=1000)
        self.c3 = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="c3", name="NC1",
            series="牛客周赛", start_time="2026-03-01T00:00:00Z",
            is_rated=True, is_paid=False, participant_count=1000)

        Participation.objects.create(contest=self.c1, platform_account=self.pa_cf_a,
                                      handle="cfa", handle_lower="cfa", rank=1)
        Participation.objects.create(contest=self.c2, platform_account=self.pa_cf_a,
                                      handle="cfa", handle_lower="cfa", rank=501)
        Participation.objects.create(contest=self.c3, platform_account=self.pa_nc_a,
                                      handle="nca", handle_lower="nca", rank=501)
        Participation.objects.create(contest=self.c1, platform_account=self.pa_cf_b,
                                      handle="cfb", handle_lower="cfb", rank=100)
        Participation.objects.create(contest=self.c1, platform_account=self.pa_cf_c,
                                      handle="cfc", handle_lower="cfc", rank=200)
        # 一条被排除的（作弊），不应参与计分
        Participation.objects.create(contest=self.c1, platform_account=self.pa_cf_a,
                                     handle="cfcheat", handle_lower="cfcheat",
                                     rank=3, is_excluded=True,
                                     exclude_reason="cheater")

    def _z(self, rank, vp=1000):
        p = min(max((rank - 0.5) / vp, 1e-6), 1 - 1e-6)
        return _NORM.inv_cdf(1 - p)

    def test_student_snapshot_values(self):
        # N=1 + decay=0：站点 rating = 最新一场 perf（跨平台取最新）
        # ua 最新一场是 c3（牛客，rank 501）→ perf = 950 + 400×z(501)
        recompute_score_records()
        recompute_snapshots(RankSnapshot.Scope.STUDENT, "all")
        ua = RankSnapshot.objects.get(scope="student", period="all", user=self.ua)
        self.assertAlmostEqual(float(ua.total_score),
                               950 + 400 * self._z(501), places=1)
        self.assertEqual(ua.contest_count, 3)  # 全部计入场次
        ub = RankSnapshot.objects.get(scope="student", period="all", user=self.ub)
        self.assertAlmostEqual(float(ub.total_score),
                               1450 + 400 * self._z(100), places=1)
        uc = RankSnapshot.objects.get(scope="student", period="all", user=self.uc)
        self.assertAlmostEqual(float(uc.total_score),
                               1450 + 400 * self._z(200), places=1)
        # 名次：ub > uc > ua（ua 最新一场只是牛客中位）
        self.assertEqual(ub.rank, 1)
        self.assertEqual(uc.rank, 2)
        self.assertEqual(ua.rank, 3)

    def test_school_snapshot_sums_member_ratings(self):
        recompute_score_records()
        recompute_snapshots(RankSnapshot.Scope.SCHOOL, "all")
        a = RankSnapshot.objects.get(scope="school", period="all",
                                     school=self.school_a)
        ua_rating = 950 + 400 * self._z(501)
        ub_rating = 1450 + 400 * self._z(100)
        self.assertAlmostEqual(float(a.total_score), ua_rating + ub_rating,
                               delta=1.0)
        self.assertEqual(a.member_count, 2)
        self.assertEqual(a.contest_count, 4)  # ua 3 + ub 1
        b = RankSnapshot.objects.get(scope="school", period="all",
                                     school=self.school_b)
        self.assertAlmostEqual(float(b.total_score),
                               1450 + 400 * self._z(200), delta=1.0)
        self.assertEqual(a.rank, 1)
        self.assertEqual(b.rank, 2)

    def test_tied_scores_share_rank_and_skip(self):
        # 构造 ub/uc 同分：同名次同场次
        Participation.objects.filter(contest=self.c1, platform_account=self.pa_cf_c)\
            .update(rank=100)
        recompute_score_records()
        recompute_snapshots(RankSnapshot.Scope.STUDENT, "all")
        snaps = {s.user_id: s for s in RankSnapshot.objects.filter(
            scope="student", period="all")}
        ub, uc = snaps[self.ub.id], snaps[self.uc.id]
        self.assertEqual(ub.rank, 1)
        self.assertEqual(uc.rank, 1)   # 同分并列
        self.assertEqual(snaps[self.ua.id].rank, 3)  # 跳位

    def test_paid_rated_contest_counts(self):
        """付费 rated 比赛同样计分（2026-09-07 用户确认：筛选只看 rated）。"""
        paid = Contest.objects.create(
            platform=Platform.NOWCODER, external_id="paid1",
            name="NC Paid", series="牛客周赛",
            start_time="2026-04-01T00:00:00Z",
            is_rated=True, is_paid=True, participant_count=1000)
        Participation.objects.create(
            contest=paid, platform_account=self.pa_nc_a,
            handle="nca", handle_lower="nca", rank=10)
        recompute_score_records()
        self.assertTrue(ScoreRecord.objects.filter(
            participation__contest=paid).exists())

    def test_period_filter_current_year(self):
        recompute_score_records()
        self.assertEqual(
            recompute_snapshots(RankSnapshot.Scope.STUDENT, "2026"), 3)
        self.assertEqual(
            recompute_snapshots(RankSnapshot.Scope.STUDENT, "2025"), 0)

    def test_recompute_all(self):
        res = recompute_all()
        self.assertIn("snapshots", res)
        self.assertEqual(len(res["snapshots"]), 4)

    # ---------- API ----------
    def test_ranking_api_list(self):
        from rest_framework.test import APIClient
        recompute_all()
        client = APIClient()
        resp = client.get("/api/v1/rankings/",
                          {"scope": "school", "period": "all"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 2)

    def test_rating_history_api(self):
        from rest_framework.test import APIClient
        recompute_all()
        client = APIClient()
        # 未带 user 且未登录 → 400
        r = client.get("/api/v1/rating-history/")
        self.assertEqual(r.status_code, 400)
        # 带 user 公开可读；时间线每场都有 rating 且与榜单一致
        r = client.get("/api/v1/rating-history/", {"user": self.ua.id})
        self.assertEqual(r.status_code, 200)
        results = r.data["results"]
        self.assertEqual(len(results), 3)
        self.assertAlmostEqual(results[-1]["rating"],
                               float(RankSnapshot.objects.get(
                                   scope="student", period="all",
                                   user=self.ua).total_score), places=1)
        # decay=0：首场 rating = perf（先验 prior=0 也被 decay=0 短路）
        self.assertEqual(results[0]["perf"], results[0]["rating"])

    def test_recompute_action_requires_super(self):
        from rest_framework.test import APIClient
        client = APIClient()
        normal = User.objects.create_user(username="normal")
        client.force_authenticate(normal)
        r = client.post("/api/v1/rankings/recompute/")
        self.assertEqual(r.status_code, 403)
        sup = User.objects.create_user(username="sup", role=UserRole.SUPER_ADMIN)
        client.force_authenticate(sup)
        r = client.post("/api/v1/rankings/recompute/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(RankSnapshot.objects.exists())


class SeasonTests(TestCase):
    """赛季信息：当前赛季懒创建、阶段推导、进度与接口返回。"""

    def test_get_current_season_lazy_creates(self):
        from django.utils import timezone
        from apps.ranking.models import Season, SeasonConfig
        from apps.ranking.season import get_current_season

        season = get_current_season()
        self.assertEqual(season.year, timezone.now().year)
        self.assertEqual(Season.objects.count(), 1)
        cfg = SeasonConfig.get_config()
        self.assertEqual(cfg.current_season, season.year)

    def test_season_number_and_default_name(self):
        """赛季序号以 2026 年为第 1 赛季逐年累加；默认名称跟随序号。"""
        import datetime

        from django.utils import timezone

        from apps.ranking.models import Season

        s2026 = Season.objects.create(
            year=2026,
            start_at=timezone.make_aware(datetime.datetime(2026, 1, 1)),
            end_at=timezone.make_aware(datetime.datetime(2026, 12, 31, 23, 59, 59)))
        self.assertEqual(s2026.number, 1)
        self.assertEqual(s2026.name, "第 1 赛季")

        s2027 = Season.objects.create(
            year=2027,
            start_at=timezone.make_aware(datetime.datetime(2027, 1, 1)),
            end_at=timezone.make_aware(datetime.datetime(2027, 12, 31, 23, 59, 59)))
        self.assertEqual(s2027.number, 2)
        self.assertEqual(s2027.name, "第 2 赛季")

        # 已有名称不被覆盖（管理员可自定义）
        s2026.name = "自定义赛季名"
        s2026.save()
        s2026.refresh_from_db()
        self.assertEqual(s2026.name, "自定义赛季名")

    def test_progress_and_countdown(self):
        import datetime
        from django.utils import timezone
        from apps.ranking.season import season_progress, settle_countdown

        now = timezone.now()
        start = now - datetime.timedelta(days=100)
        end = now + datetime.timedelta(days=265)
        class _S:
            start_at = start
            end_at = end
            settle_at = now + datetime.timedelta(days=10)
        s = _S()
        p = season_progress(s, now)
        self.assertEqual(p["total_days"], 365)
        self.assertGreater(p["pct"], 0)
        cd = settle_countdown(s, now)
        self.assertGreater(cd, 0)

    def test_season_api_public_and_me(self):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient
        User = get_user_model()
        client = APIClient()
        # 未登录：公开可读，me 为 None
        r = client.get("/api/v1/season/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("year", r.data)
        self.assertIsNone(r.data.get("me"))
        # 登录用户：me 附带战绩
        u = User.objects.create_user(username="s1", password="pwd12345")
        client.force_authenticate(u)
        r = client.get("/api/v1/season/")
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.data.get("me"))
        self.assertEqual(r.data["me"]["total_score"], 0)


class UserBestRecordTests(TestCase):
    """历史最佳 = 比赛演变重演：每个赛后时点各用户取站点 rating，
    对全体用户排序，best_rank/best_score 取全部时点中的最优。
    （此处锁定 decay=0 的「最新一场」口径，与既有用例语义一致）"""

    def setUp(self):
        make_config(recent_limit=1, decay=0.0, prior=0.0)

    def _seed(self, username, platform, score, when, school=None):
        """造一条 countable 积分记录（User+PA+Contest+Participation+ScoreRecord）。"""
        from datetime import timedelta

        from django.utils import timezone as tz

        user = User.objects.filter(username=username).first()
        if user is None:
            user = User.objects.create_user(username=username, password="Test1234!",
                                            school=school)
        pa, _ = PlatformAccount.objects.get_or_create(
            user=user, platform=platform,
            defaults={"handle": f"{username}_{platform}",
                      "handle_lower": f"{username}_{platform}"})
        day = when.date()
        contest, _ = Contest.objects.get_or_create(
            platform=platform, external_id=f"ex-{username}-{day.isoformat()}",
            defaults={"name": f"C-{username}-{day}", "is_rated": True,
                      "start_time": when, "end_time": when + timedelta(hours=2)})
        part, _ = Participation.objects.get_or_create(
            contest=contest, platform_account=pa,
            defaults={"handle": pa.handle, "handle_lower": pa.handle_lower,
                      "is_excluded": False})
        ScoreRecord.objects.update_or_create(
            participation=part,
            defaults={"platform_account": pa, "platform": platform,
                      "final_score": score, "contest_time": when})
        return user

    def test_replay_rank_history(self):
        from datetime import datetime

        from django.utils import timezone as tz

        def at(s):
            return tz.make_aware(datetime.strptime(s, "%Y-%m-%d %H:%M"))

        # A：t1 500 分（此时唯一学生 → #1）；t3 涨到 600
        a = self._seed("rep_a", Platform.CODEFORCES, 500.0, at("2026-01-01 10:00"))
        b = self._seed("rep_b", Platform.NOWCODER, 400.0, at("2026-01-02 10:00"))
        self._seed("rep_a", Platform.CODEFORCES, 600.0, at("2026-01-03 10:00"))
        update_user_best_records()

        ra = UserBestRecord.objects.get(user=a)
        # A 从 t1 起一直 #1，同名次配对更高 rating → (1, 600.0, t3)
        self.assertEqual(ra.best_rank, 1)
        self.assertEqual(ra.best_rank_score, 600.0)
        self.assertEqual(ra.best_score, 600.0)
        rb = UserBestRecord.objects.get(user=b)
        # B 在 t2 进入后始终低于 A → #2 / 400
        self.assertEqual(rb.best_rank, 2)
        self.assertEqual(rb.best_rank_score, 400.0)
        self.assertEqual(rb.best_score, 400.0)
        self.assertEqual(rb.best_score_rank, 2)

    def test_best_rank_can_precede_higher_score(self):
        from datetime import datetime

        from django.utils import timezone as tz

        def at(s):
            return tz.make_aware(datetime.strptime(s, "%Y-%m-%d %H:%M"))

        # A 先得 800（独占榜单 → #1）后跌到 300；B 在下跌后以 500 加入 → B#1, A#2
        a = self._seed("pre_a", Platform.CODEFORCES, 800.0, at("2026-02-01 10:00"))
        self._seed("pre_a", Platform.CODEFORCES, 300.0, at("2026-02-03 10:00"))
        b = self._seed("pre_b", Platform.NOWCODER, 500.0, at("2026-02-03 10:00"))
        update_user_best_records()

        ra = UserBestRecord.objects.get(user=a)
        # A 的最佳名次在早期 #1（当时 rating 800），最佳 rating 也是 800
        self.assertEqual(ra.best_rank, 1)
        self.assertEqual(ra.best_rank_score, 800.0)
        self.assertEqual(ra.best_score, 800.0)
        rb = UserBestRecord.objects.get(user=b)
        # B 首秀即 #1（500 > 300），配对 500
        self.assertEqual(rb.best_rank, 1)
        self.assertEqual(rb.best_rank_score, 500.0)

    def test_orphan_cleanup(self):
        from django.utils import timezone as tz

        u = User.objects.create_user(username="orph", password="Test1234!")
        UserBestRecord.objects.create(
            user=u, best_rank=1, best_rank_score=1.0, best_rank_at=tz.now(),
            best_score=1.0, best_score_rank=1, best_score_at=tz.now())
        update_user_best_records()  # 无任何积分记录 → 纪录被清理
        self.assertFalse(UserBestRecord.objects.filter(user=u).exists())

    def test_rating_history_matches_replay(self):
        """rating_history 与最佳纪录重演共用同一口径：最新点 = 当前窗口 rating。"""
        from datetime import datetime

        from django.utils import timezone as tz

        def at(s):
            return tz.make_aware(datetime.strptime(s, "%Y-%m-%d %H:%M"))

        a = self._seed("rh_a", Platform.CODEFORCES, 500.0, at("2026-03-01 10:00"))
        self._seed("rh_a", Platform.CODEFORCES, 700.0, at("2026-03-02 10:00"))
        hist = rating_history(a.id)
        self.assertEqual(len(hist), 2)
        # decay=0：最新一场即 rating
        self.assertEqual(hist[-1]["rating"], 700)
        self.assertEqual(hist[-1]["perf"], 700)
