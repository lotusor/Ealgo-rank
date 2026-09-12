"""按牛客账号索引补抓本站未收录的 rated 历史比赛。

背景（2026-09-09，Chen777iii 案例）：账号索引（participated_contests，来自
官方 rating-history 接口，只含 rated 场次）里指向的历史比赛，因爬取窗口
（months_back）限制从未入库，导致历史成绩缺失、折线图不完整。

流程：对牛客 PlatformAccount 的索引并集中「本站未收录」的源站比赛 id，
逐场 fetch_contest_info 判 rated → rated 则抓取榜单 → ingest_contest 入库
→ 全量重算积分。

用法：
  python manage.py backfill_indexed_nowcoder --dry-run      # 只列出待补抓清单
  python manage.py backfill_indexed_nowcoder                # 实抓（全部）
  python manage.py backfill_indexed_nowcoder --limit 5      # 限本次场数
  python manage.py backfill_indexed_nowcoder --account 14   # 限定账号
"""
import sys

from django.core.management.base import BaseCommand

from apps.common.models import Platform
from apps.contests.models import Contest
from apps.accounts.models import PlatformAccount


class Command(BaseCommand):
    help = "按牛客账号索引补抓本站未收录的 rated 历史比赛"

    def add_arguments(self, parser):
        parser.add_argument(
            "--account", type=int, default=None,
            help="限定 PlatformAccount id（默认全部牛客账号）")
        parser.add_argument("--dry-run", action="store_true",
                            help="只列出待补抓清单，不抓取")
        parser.add_argument(
            "--limit", type=int, default=0,
            help="本次最多抓取场数（0=不限）")

    def handle(self, *args, **opts):
        from apps.crawler.ingest import ingest_contest
        from apps.crawler.tasks import _crawler_cache_dir
        from apps.ranking.engine import (recompute_score_records,
                                         recompute_snapshots,
                                         update_user_best_records)
        from apps.ranking.models import RankSnapshot

        sys.path.insert(0, "/app/crawlers")
        from nowcoder_scraper import NowCoderScraper  # noqa: E402

        qs = PlatformAccount.objects.filter(platform=Platform.NOWCODER)
        if opts["account"]:
            qs = qs.filter(id=opts["account"])

        scraper = NowCoderScraper()
        scraper.init_session()

        # 索引并集中本站未收录的源站比赛 id
        have = set(Contest.objects.filter(
            platform=Platform.NOWCODER).values_list("external_id", flat=True))
        pending = {}
        for acc in qs:
            for cid in (acc.participated_contests or []):
                cid = str(cid)
                if cid and cid not in have:
                    pending.setdefault(cid, []).append(acc.handle)

        self.stdout.write(f"待补抓源站比赛: {len(pending)}")
        if not pending:
            self.stdout.write(self.style.SUCCESS("nothing to do"))
            return

        if opts["dry_run"]:
            for cid in sorted(pending, key=int, reverse=True):
                self.stdout.write(f"  src={cid} accounts={pending[cid]}")
            return

        cache_dir = _crawler_cache_dir(Platform.NOWCODER)
        limit = opts["limit"] or len(pending)
        ingested = skipped = failed = 0
        for i, cid in enumerate(sorted(pending, key=int, reverse=True), 1):
            if i > limit:
                self.stdout.write(f"已达 --limit {limit}，剩余 {len(pending) - i + 1} 场下次再跑")
                break
            try:
                info = scraper.fetch_contest_info(cid, use_cache=False)
                if not info:
                    failed += 1
                    self.stdout.write(f"[{i}/{len(pending)}] {cid} 详情获取失败")
                    continue
                meta = scraper.check_rated({"real_contest_id": cid})
                start_ts, end_ts = info.get("startTime"), info.get("endTime")
                meta.update({
                    "real_contest_id": cid,
                    "contest_id": cid,
                    "name": info.get("name") or str(cid),
                    "start_time": scraper._ts2str(start_ts),
                    "end_time": scraper._ts2str(end_ts),
                    "duration_minutes": (int((end_ts - start_ts) / 60000)
                                         if start_ts and end_ts else None),
                    "link": f"https://www.nowcoder.com/acm/contest/{cid}",
                })
                if not meta.get("is_rated"):
                    skipped += 1
                    self.stdout.write(
                        f"[{i}/{len(pending)}] {cid} {meta['name'][:24]} "
                        f"非 rated 跳过（{meta.get('rated_comment')}）")
                    continue
                detail = scraper.scrape_contest_detail(
                    cid, filter_post_contest=True, exclude_cheaters=False,
                    cache_dir=cache_dir)
                result = ingest_contest(Platform.NOWCODER, meta, detail)
                if result.get("skipped"):
                    skipped += 1
                    self.stdout.write(
                        f"[{i}/{len(pending)}] {cid} 跳过: {result.get('reason')}")
                    continue
                ingested += 1
                self.stdout.write(
                    f"[{i}/{len(pending)}] {cid} {meta['name'][:24]} 入库 "
                    f"计分 {result['countable']} 条")
            except Exception as exc:  # noqa: BLE001 - 单场失败不阻断
                failed += 1
                self.stdout.write(f"[{i}/{len(pending)}] {cid} 异常: {exc}")

        self.stdout.write(
            f"补抓完成: 入库 {ingested} / 跳过 {skipped} / 失败 {failed}")

        if ingested:
            self.stdout.write("触发全量积分重算…")
            sr = recompute_score_records()
            self.stdout.write(
                f"ScoreRecord: +{sr['created']} ~{sr['updated']} "
                f"-{sr.get('deleted', 0)}")
            for sc in (RankSnapshot.Scope.SCHOOL, RankSnapshot.Scope.STUDENT):
                for pd in ("all", str(__import__("datetime").datetime.now().year)):
                    n = recompute_snapshots(sc, pd)
                    self.stdout.write(f"snapshot[{sc}/{pd}]: {n} rows")
            update_user_best_records()
        self.stdout.write(self.style.SUCCESS("done"))
