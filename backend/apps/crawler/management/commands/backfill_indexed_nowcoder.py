"""定向补齐牛客账号的历史参赛记录（手动/一次性修复入口）。

待补口径是「官方参赛索引里有、但这个账号在库里没有参赛行」，索引 = rating-history
∪ 个人主页已结束场次（后者是超集，见 HANDOVER §0.23 附），覆盖两类缺口：
  1. 比赛从未入库（2026-09-09 Chen777iii 案例，旧版命令只处理这一类）；
  2. 比赛早已入库、只缺这个账号那一行（2026-09-22 学生榜第一名案例，
     21 场缺失里 20 场属于这类——旧版命令按「比赛未入库」筛选，永远修不掉）。

抓取顺序是「本地已有榜单原文先做」：这些原文通常已在 crawlers/data/nowcoder
里（一场的 JSON 1~17MB），零网络即可重放入库；否则要按 50 条/页 + 1.5~3.5s
延时整场翻页，单场 90~300 秒。

用法：
  python manage.py backfill_indexed_nowcoder --dry-run      # 只列待补清单
  python manage.py backfill_indexed_nowcoder                # 全部牛客账号
  python manage.py backfill_indexed_nowcoder --account 17   # 限定账号
  python manage.py backfill_indexed_nowcoder --limit 5      # 每账号最多几场
"""
from django.core.management.base import BaseCommand

from apps.accounts.models import PlatformAccount
from apps.common.models import Platform
from apps.crawler.ingest import _crawler_dir, backfill_account_history


class Command(BaseCommand):
    help = "按牛客账号索引补抓本站缺失的历史参赛记录"

    def add_arguments(self, parser):
        parser.add_argument(
            "--account", type=int, default=None,
            help="限定 PlatformAccount id（默认全部牛客账号）")
        parser.add_argument("--dry-run", action="store_true",
                            help="只列出待补清单，不抓取")
        parser.add_argument(
            "--limit", type=int, default=0,
            help="每个账号本次最多抓取场数（0=不限）")

    def handle(self, *args, **opts):
        from apps.ranking.engine import (recompute_score_records,
                                        recompute_snapshots,
                                        update_user_best_records)
        from apps.ranking.models import RankSnapshot

        qs = PlatformAccount.objects.filter(platform=Platform.NOWCODER)
        if opts["account"]:
            qs = qs.filter(id=opts["account"])

        scraper = None
        if not opts["dry_run"]:
            _crawler_dir()
            from nowcoder_scraper import NowCoderScraper
            scraper = NowCoderScraper()
            scraper.init_session()

        ingested = 0
        for acc in qs.order_by("id"):
            self.stdout.write(f"== acc#{acc.pk} user={acc.user_id} "
                              f"handle={acc.handle} ==")
            stats = backfill_account_history(
                acc, scraper=scraper, limit=opts["limit"],
                dry_run=opts["dry_run"], log=self.stdout.write)
            ingested += stats.get("ingested", 0)
            self.stdout.write(
                f"   待补 {stats['pending']} / 入库 {stats.get('ingested', 0)}"
                f" / 跳过 {stats.get('skipped', 0)}"
                f" / 失败 {stats.get('failed', 0)}")
            v = stats.get("verify")
            if v is not None:
                parts = [f"{k}={len(v[k])}" for k in
                         ("missing_rows", "rank_diff", "delta_diff", "ac_diff",
                          "unrated_rows") if v.get(k)]
                self.stdout.write("   主页对账：" + (" ".join(parts) or "无差异"))

        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("dry-run done"))
            return
        self.stdout.write(f"合计入库 {ingested} 场")
        if ingested:
            self.stdout.write("触发全量积分重算…")
            sr = recompute_score_records()
            self.stdout.write(
                f"ScoreRecord: +{sr['created']} ~{sr['updated']} "
                f"-{sr.get('deleted', 0)}")
            import datetime
            for sc in (RankSnapshot.Scope.SCHOOL, RankSnapshot.Scope.STUDENT):
                for pd in ("all", str(datetime.datetime.now().year)):
                    n = recompute_snapshots(sc, pd)
                    self.stdout.write(f"snapshot[{sc}/{pd}]: {n} rows")
            update_user_best_records()
        self.stdout.write(self.style.SUCCESS("done"))
