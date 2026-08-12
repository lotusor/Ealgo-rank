"""
演示种子数据：构造学校 / 学生 / 平台账号 / 比赛(rated) / 参赛记录，
然后跑 recompute 生成 RankSnapshot，让 /rankings/ 与用户端有真实可展示内容。

设计：
- 6 所学校，每校 20 名学生，按学校强度赋予不同“水平”，使学校榜有自然差距。
- 每名学生随机绑定 1~3 个平台账号（CF / AtCoder / 牛客）。
- 每平台 12 场 rated 比赛，分布在近 6 个月；每场由该平台有账号的学生参赛，
  名次按“水平 + 噪声”排序，rating/new_rating/rating_delta 一并生成。
- 全部 is_excluded=False、contest rated 且非付费，确保进入积分引擎 countable。

幂等：所有对象用稳定唯一键 get_or_create，重复执行不会重复建；
但已存在的参赛记录不会被覆盖（名次/分数保持首次生成值）。

用法：
    python manage.py seed_demo
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import PlatformAccount, User, UserRole
from apps.common.models import Platform
from apps.contests.models import Contest, Participation
from apps.ranking.engine import recompute_all
from apps.schools.models import School

SCHOOLS = [
    ("清华大学", "thu", "THU"),
    ("北京大学", "pku", "PKU"),
    ("浙江大学", "zju", "ZJU"),
    ("上海交通大学", "sjtu", "SJTU"),
    ("复旦大学", "fdu", "FDU"),
    ("电子科技大学", "uestc", "UESTC"),
]
PLATFORMS = [Platform.CODEFORCES, Platform.ATCODER, Platform.NOWCODER]
STUDENTS_PER_SCHOOL = 20
CONTESTS_PER_PLATFORM = 12
SEED = 20260805


class Command(BaseCommand):
    help = "构造演示种子数据并重算榜单快照"

    def handle(self, *args, **options):
        random.seed(SEED)
        now = timezone.now()

        # 1) 学校
        schools = []
        for name, code, short in SCHOOLS:
            s, _ = School.objects.get_or_create(
                code=code,
                defaults={"name": name, "short_name": short, "is_active": True},
            )
            schools.append(s)
        self.stdout.write(f"学校：{len(schools)} 所")

        # 2) 学生（带水平分，按学校强度偏移）
        students = []  # (user, skill, school)
        for idx, s in enumerate(schools):
            base = 1500 + idx * 90  # 学校整体水平
            for i in range(1, STUDENTS_PER_SCHOOL + 1):
                username = f"{s.code}_stu{i:02d}"
                u, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": f"{username}@example.com",
                        "real_name": f"{s.short_name}学生{i}",
                        "student_no": f"{s.code}{i:04d}",
                        "role": UserRole.USER,
                        "school": s,
                        "school_bound_at": now,
                    },
                )
                if created:
                    u.set_password("test1234")
                    u.save()
                skill = base + random.randint(-220, 220)
                students.append((u, skill, s))
        self.stdout.write(f"学生：{len(students)} 人")

        # 3) 平台账号
        pa_map = {}
        for u, skill, s in students:
            n_plat = random.choice([1, 2, 2, 3])
            for p in random.sample(PLATFORMS, n_plat):
                handle = f"{s.code}_{p}_{u.username.split('_')[-1]}"
                pa, _ = PlatformAccount.objects.get_or_create(
                    user=u, platform=p,
                    defaults={"handle": handle, "display_name": u.real_name},
                )
                pa_map[(u.id, p)] = pa
        self.stdout.write(f"平台账号：{len(pa_map)} 个")

        # 4) 比赛（每平台近 6 个月，rated 且免费）
        contests = []
        for p in PLATFORMS:
            for c in range(CONTESTS_PER_PLATFORM):
                days_ago = 180 - c * 15
                start = now - timedelta(days=days_ago)
                ext = f"seed_{p}_{c}"
                contest, _ = Contest.objects.get_or_create(
                    platform=p, external_id=ext,
                    defaults={
                        "name": f"{p} Round {c + 1}",
                        "url": f"https://example.com/{p}/{c}",
                        "start_time": start,
                        "end_time": start + timedelta(hours=2),
                        "duration_minutes": 120,
                        "is_rated": True,
                        "is_paid": False,
                        "series": f"{p} Series",
                        "difficulty_factor": round(random.uniform(1.0, 1.3), 3),
                        "problem_count": random.randint(5, 8),
                    },
                )
                contests.append((contest, p))
        self.stdout.write(f"比赛：{len(contests)} 场")

        # 5) 参赛记录
        created_p = 0
        for contest, p in contests:
            ranked = sorted(
                [(u, sk, s) for (u, sk, s) in students if (u.id, p) in pa_map],
                key=lambda x: x[1] + random.randint(-150, 150),
                reverse=True,
            )
            n = len(ranked)
            for rank, (u, skill, s) in enumerate(ranked, 1):
                pa = pa_map[(u.id, p)]
                old = max(800, skill + random.randint(-100, 100))
                delta = random.randint(-35, 65)
                new = old + delta
                _, was_created = Participation.objects.get_or_create(
                    contest=contest, platform_account=pa,
                    defaults={
                        "rank": rank,
                        "solved_count": max(0, 8 - rank // 3),
                        "penalty_ms": rank * 60000,
                        "old_rating": old,
                        "new_rating": new,
                        "rating_delta": delta,
                        "handle": pa.handle,
                        "is_excluded": False,
                        "exclude_reason": "",
                    },
                )
                if was_created:
                    created_p += 1
            contest.participant_count = n
            contest.valid_participant_count = n
            contest.save(update_fields=["participant_count", "valid_participant_count"])
        self.stdout.write(f"参赛记录（新建）：{created_p}")

        # 6) 重算积分与榜单
        result = recompute_all()
        self.stdout.write(self.style.SUCCESS(f"种子完成：{result}"))
