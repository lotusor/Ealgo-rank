"""按拆榜口径重灌牛客场次（打星适配的一次性回填入口）。

为什么现有命令修不了这次的问题：
  `backfill_indexed_nowcoder` / `sweep_nowcoder_history` 的待补口径是
  「索引里有、库里缺这一行」。而打星适配改的是**已经在库里的行**：
    1. 打星学生的行要从「计分」改成 `exclude_reason=star`；
    2. `Contest.participant_count` 要从混排总人数改成正式榜人数（表现分分母）；
    3. 所有人的 `rank` 要从混排名次改成榜内名次。
  这三项都只能靠**重新入库那一场比赛的榜单**得出，缺行的补数路径碰不到它们。

抓取来源同日常爬取：本地榜单原文命中即零网络。但旧原文是拆榜前的解析产物
（没有 participation_type），会被 `cache_util` 的结构版本闸挡掉并重新下载 ——
这正是我们要的，否则会静默得出「这场没人打星」。

用法：
  python manage.py reingest_nowcoder_boards --dry-run
  python manage.py reingest_nowcoder_boards --since 2026-10-01
  python manage.py reingest_nowcoder_boards --ids 141142,141721
  python manage.py reingest_nowcoder_boards --force      # 已重灌过的也再来一遍
"""
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.common.models import Platform
from apps.contests.models import (CALENDAR_RATED_SOURCE, Contest,
                                  Participation)
from apps.crawler.ingest import _crawler_dir, _meta_from_contest, ingest_contest


def with_star_meta(scraper, meta):
    """给重灌用的 meta 补上打星元数据。

    回填的 meta 来自 `_meta_from_contest`，它沿用**入库当时**的 raw_meta，不会重跑
    `check_rated` → 不补这一步，已入库场次的 raw_meta 里永远没有
    allow_star_participation / rating_upper_limit / participation_enabled，
    而 D4（元数据落库）恰恰要对这些已在库的场次生效。一次 contest-info 换一次判定，
    比等下一轮月度爬取重新判更直接；取不到就照旧，不阻断重灌。
    """
    if "allow_star_participation" in meta:
        return meta
    try:
        flags = scraper.check_rated({"real_contest_id": meta.get("real_contest_id")})
    except Exception:  # noqa: BLE001 - 元数据缺失不该挡住积分口径修正
        return meta
    if not flags or flags.get("is_rated") is None:
        return meta
    out = dict(meta)
    for key in ("allow_star_participation", "rating_upper_limit",
                "participation_enabled", "rated_comment"):
        if key in flags:
            out[key] = flags[key]
    return out


class Command(BaseCommand):
    help = "重新入库牛客场次，把打星排除、正式榜分母与榜内名次补进已在库的行"

    def add_arguments(self, parser):
        parser.add_argument(
            "--since", type=str, default="2026-10-01",
            help="只重灌开始时间不早于该日的场次。打星是 2026-10-04 的周赛 Round 164 "
                 "才上线的（Round 163=2026-09-27 没有），默认留几天余量；"
                 "更早的场次没有打星，重灌只烧流量。逐场的准确标志是入库后 "
                 "raw_meta.participation_enabled，需要时用 --ids 精确点名")
        parser.add_argument("--ids", type=str, default="",
                            help="逗号分隔的 Contest.external_id，指定后忽略 --since")
        parser.add_argument("--limit", type=int, default=0,
                            help="本次最多重灌几场（0=不限）")
        parser.add_argument("--force", action="store_true",
                            help="连已经带 board_counts 的场次也再来一遍")
        parser.add_argument("--dry-run", action="store_true", help="只列清单")

    def _candidates(self, opts):
        qs = Contest.objects.filter(platform=Platform.NOWCODER, is_rated=True)
        if opts["ids"]:
            wanted = [x.strip() for x in opts["ids"].split(",") if x.strip()]
            qs = qs.filter(external_id__in=wanted)
        else:
            since = timezone.make_aware(
                datetime.strptime(opts["since"], "%Y-%m-%d"),
                timezone.get_current_timezone())
            qs = qs.filter(start_time__gte=since)
        # 三道必要的收口：
        #  · 日历排期行的 is_rated 只是预告期预判，它没有榜单，重灌等于抓空场；
        #  · 未结束的场次榜单还在变，日常爬取本来就按 endTime 跳过（tasks._ended），
        #    这里跟着抓会写入半程榜单；
        #  · 只重灌「已在库有参赛行」的场次 —— 本命令修的是已在库的行，空场次
        #    没有可修的对象，抓一场 24 页榜单纯属烧流量与巡检预算。
        qs = (qs.exclude(rated_source=CALENDAR_RATED_SOURCE)
                .filter(end_time__lte=timezone.now())
                .filter(participations__isnull=False)
                .distinct())
        return list(qs.order_by("-start_time"))

    def handle(self, *args, **opts):
        rows = self._candidates(opts)
        # 「已重灌过」的标记在 raw_meta 的键上，不能在 SQL 里 exclude(has_key=...)：
        # SQLite 对 JSONField 键的 NOT + NULL 三值逻辑会把「不含该键」的行一起滤掉
        # （见 AGENTS.md §7），本地跑就会变成一行都选不出来。留在 Python 侧筛。
        if not opts["force"] and not opts["ids"]:
            rows = [c for c in rows if "board_counts" not in (c.raw_meta or {})]
        if opts["limit"]:
            rows = rows[:opts["limit"]]

        self.stdout.write(f"待重灌 {len(rows)} 场"
                          f"（{'ids 指定' if opts['ids'] else 'since=' + opts['since']}，"
                          f"force={opts['force']}）")
        for c in rows[:20]:
            self.stdout.write(f"  {c.external_id} {c.name[:34]} "
                              f"在库 {c.participations.count()} 行")
        if len(rows) > 20:
            self.stdout.write(f"  ...（其余 {len(rows) - 20} 场略）")
        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("dry-run done"))
            return

        _crawler_dir()
        from nowcoder_scraper import NowCoderScraper

        from apps.crawler.tasks import _contest_cache_ttl, _crawler_cache_dir

        scraper = NowCoderScraper()
        scraper.init_session()
        cache_dir = _crawler_cache_dir(Platform.NOWCODER)

        total_star = total_flip_out = total_rank_changed = failed = 0
        for c in rows:
            meta = with_star_meta(scraper, _meta_from_contest(c))
            before = {p.handle_lower: p
                      for p in Participation.objects.filter(contest=c)}
            before_countable = {h for h, p in before.items()
                                if not p.is_excluded and p.platform_account_id}
            before_ranks = {h: p.rank for h, p in before.items()}
            try:
                detail = scraper.scrape_contest_detail(
                    c.external_id, filter_post_contest=True,
                    exclude_cheaters=False, cache_dir=cache_dir,
                    cache_ttl_hours=_contest_cache_ttl(meta))
                res = ingest_contest(Platform.NOWCODER, meta, detail)
            except Exception as exc:  # noqa: BLE001 - 单场失败不阻断其余
                failed += 1
                self.stdout.write(self.style.ERROR(f"{c.external_id} 失败: {exc}"))
                continue
            if res.get("skipped"):
                self.stdout.write(f"{c.external_id} 跳过: {res.get('reason')}")
                continue
            c.refresh_from_db()
            after = {p.handle_lower: p
                     for p in Participation.objects.filter(contest=c)}
            after_countable = {h for h, p in after.items()
                               if not p.is_excluded and p.platform_account_id}
            flipped = sorted(before_countable - after_countable)
            rank_changed = sum(1 for h, rk in before_ranks.items()
                               if h in after and after[h].rank != rk)
            total_star += res.get("stars", 0)
            total_flip_out += len(flipped)
            total_rank_changed += rank_changed
            self.stdout.write(
                f"{c.external_id} {c.name[:28]}: 打星排除 {res.get('stars', 0)} 行，"
                f"计分 {res['countable']} 行，分母(正式榜) {c.participant_count}，"
                f"名次改号 {rank_changed} 行"
                + (f" 退出积分: {flipped[:5]}" if flipped else ""))

        self.stdout.write(
            f"\n合计：打星标记排除 {total_star} 行 / 原计入积分现退出 {total_flip_out} 行 / "
            f"名次改为榜内名次 {total_rank_changed} 行 / 失败 {failed} 场")

        from apps.ranking.engine import (recompute_score_records,
                                        recompute_snapshots,
                                        update_user_best_records)
        from apps.ranking.models import RankSnapshot

        self.stdout.write("触发全量积分重算…")
        sr = recompute_score_records()
        self.stdout.write(f"ScoreRecord: +{sr['created']} ~{sr['updated']} -{sr['deleted']}")
        year = str(timezone.now().year)
        for sc in (RankSnapshot.Scope.SCHOOL, RankSnapshot.Scope.STUDENT):
            for pd in ("all", year):
                n = recompute_snapshots(sc, pd)
                self.stdout.write(f"snapshot[{sc}/{pd}]: {n} rows")
        update_user_best_records()
        self.stdout.write(self.style.SUCCESS("done"))
