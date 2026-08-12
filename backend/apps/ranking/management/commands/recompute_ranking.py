"""重算积分与榜单快照。

用法：
  python manage.py recompute_ranking                 # 全量（ScoreRecord + 各 scope/period 快照）
  python manage.py recompute_ranking --scope school  # 只重算学校榜
  python manage.py recompute_ranking --period 2026  # 只重算 2026 周期
  python manage.py recompute_ranking --skip-records # 跳过 ScoreRecord，只重建快照
"""
from django.core.management.base import BaseCommand

from apps.ranking.engine import ALL_PERIODS, recompute_all, recompute_snapshots
from apps.ranking.models import RankSnapshot


class Command(BaseCommand):
    help = "重算 ScoreRecord 与 RankSnapshot（积分排名引擎）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--scope", choices=["school", "student", "all"], default="all")
        parser.add_argument(
            "--period",
            default=None,
            help="指定周期（如 2026 / 2026-08）；省略则覆盖 ALL_PERIODS")
        parser.add_argument(
            "--skip-records", action="store_true",
            help="跳过 ScoreRecord 重算，只重建快照")

    def handle(self, *args, **options):
        scope = options["scope"]
        period = options["period"]
        periods = [period] if period else ALL_PERIODS

        if not options["skip_records"]:
            from apps.ranking.engine import recompute_score_records
            sr = recompute_score_records()
            self.stdout.write(
                f"ScoreRecord: +{sr['created']} ~{sr['updated']} "
                f"-{sr.get('deleted', 0)}")
        else:
            self.stdout.write("skip ScoreRecord")

        scopes = ([scope] if scope != "all"
                  else [RankSnapshot.Scope.SCHOOL, RankSnapshot.Scope.STUDENT])
        for sc in scopes:
            for pd in periods:
                n = recompute_snapshots(sc, pd)
                self.stdout.write(f"snapshot[{sc}/{pd}]: {n} rows")
        self.stdout.write(self.style.SUCCESS("done"))
