"""重建「参与比赛索引」：把每个 PlatformAccount 参与过的比赛 external_id 写入
PlatformAccount.participated_contests。

来源：
  1. 参与记录表回填：Participation.platform_account 已知的所有 contest.external_id
     （爬虫已入库的比赛，天然就是「有已关联平台ID用户参与」的比赛）。
  2. 官方「个人参赛历史」接口廉价补全（无需下载全量榜单）：
     - Codeforces: /api/user.rating?handle=H  -> contestId 列表
     - AtCoder:    /users/{handle}/history/json -> 比赛 id 列表
     - 牛客：无干净的个人历史接口，仅依赖 ① 回填；新牛客用户需一次 force_full
       爬取（或手动触发）来发现其参赛比赛。

用途：爬虫预筛「只抓有已关联平台ID用户参与的比赛」，大幅减少无关全量榜单下载。
这里的「用户」指所有已关联竞赛平台ID的 PlatformAccount 持有者，不限学校。

    python manage.py rebuild_participation_index
    python manage.py rebuild_participation_index --platform codeforces
    python manage.py rebuild_participation_index --handle tourist
"""

import logging
import os
import sys

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.accounts.models import PlatformAccount
from apps.common.models import Platform
from apps.contests.models import Participation

logger = logging.getLogger(__name__)

# 与 crawler/tasks.py 一致：把爬虫脚本目录加入 sys.path 后导入
_CRAWLER_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "crawlers"))
if _CRAWLER_DIR not in sys.path:
    sys.path.insert(0, _CRAWLER_DIR)

from cf_scraper import CodeforcesScraper          # noqa: E402
from atcoder_scraper import AtCoderScraper        # noqa: E402


class Command(BaseCommand):
    help = "重建 PlatformAccount.participated_contests（参与比赛索引）"

    def add_arguments(self, parser):
        parser.add_argument("--platform", default=None,
                            choices=[p[0] for p in Platform.choices],
                            help="只重建指定平台（默认全部）")
        parser.add_argument("--handle", default=None,
                            help="只重建指定 handle 的账号（调试用）")

    def handle(self, *args, **options):
        platform = options.get("platform")
        handle = options.get("handle")

        qs = PlatformAccount.objects.all()
        if platform:
            qs = qs.filter(platform=platform)
        if handle:
            qs = qs.filter(handle=handle)
        total = qs.count()
        self.stdout.write(f"待处理 PlatformAccount: {total}")

        cf = CodeforcesScraper()
        atc = AtCoderScraper()

        updated = 0
        for idx, acc in enumerate(qs.iterator(), 1):
            ids = set(acc.participated_contests or [])
            # ① 参与记录表回填
            ids |= set(Participation.objects.filter(
                platform_account=acc).values_list("contest__external_id", flat=True))
            # ② 官方个人历史接口廉价补全（CF / AT）
            if acc.platform == Platform.CODEFORCES and acc.handle:
                ids |= set(cf.user_rating_contest_ids(acc.handle))
            elif acc.platform == Platform.ATCODER and acc.handle:
                ids |= set(atc.user_history_contest_ids(acc.handle))
            # 牛客无干净个人历史接口，仅依赖 ①

            ids.discard(None)
            ids.discard("")
            merged = sorted(ids)
            if merged != list(acc.participated_contests or []):
                acc.participated_contests = merged
                acc.save(update_fields=["participated_contests", "updated_at"])
                updated += 1
            if idx % 50 == 0:
                self.stdout.write(f"  ... {idx}/{total}")

        self.stdout.write(self.style.SUCCESS(
            f"完成：更新 {updated}/{total} 个账号的参与比赛索引"))
