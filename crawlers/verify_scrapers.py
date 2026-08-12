#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三平台抓取脚本联网验证工具
- 真实调用 Codeforces / AtCoder / 牛客 接口，抓取样本比赛
- 校验统一契约字段是否齐全，并统计每个字段的非空填充率
- 用法：python verify_scrapers.py [cf|at|nc|all]
"""

import json
import sys
import time
from pathlib import Path

from atcoder_scraper import AtCoderScraper
from cf_scraper import CodeforcesScraper
from nowcoder_scraper import NowCoderScraper

CONTEST_FIELDS = [
    "contest_id", "real_contest_id", "name", "oj", "link",
    "start_time", "end_time", "duration_minutes",
]
RANK_FIELDS = [
    "rank", "uid", "user_name", "school", "team", "accepted_count",
    "total_score", "full_score", "penalty_time_ms", "color_level",
    "post_contest_append", "score_detail", "extra",
]
SCORE_FIELDS = [
    "problem", "problem_id", "accepted", "score", "failed_count",
    "reach_time_ms", "first_blood", "post_contest_score",
]
PROBLEM_FIELDS = [
    "index", "title", "problem_id", "score", "total_score",
    "submit_count", "accepted_count", "submit_person_count",
]

PASS, FAIL = "PASS", "FAIL"
_results = []


def check(label, cond, note=""):
    status = PASS if cond else FAIL
    _results.append((status, label, note))
    print(f"  [{status}] {label}" + (f"  {note}" if note else ""))
    return cond


def fill_rate(rows, fields):
    """统计每个字段的非空填充率"""
    n = len(rows) or 1
    out = {}
    for f in fields:
        c = sum(1 for r in rows if r.get(f) not in (None, "", [], {}))
        out[f] = f"{c}/{len(rows)}"
    return out


def audit(platform, contests, detail, expect_school=None, expect_scoredetail=True):
    print(f"\n--- {platform} 字段审计 ---")
    # 比赛列表契约
    miss = [f for f in CONTEST_FIELDS if f not in (contests[0] if contests else {})]
    check(f"{platform} 比赛列表字段齐全", not miss, f"缺失={miss}" if miss else "")
    if contests:
        print("  比赛样例:", json.dumps(contests[0], ensure_ascii=False)[:220])

    problems = detail.get("problems", [])
    ranks = detail.get("ranks", [])
    check(f"{platform} 题目列表非空", len(problems) > 0, f"{len(problems)} 题")
    check(f"{platform} 排名非空", len(ranks) > 0, f"{len(ranks)} 条")
    if not ranks:
        return

    miss = [f for f in PROBLEM_FIELDS if problems and f not in problems[0]]
    check(f"{platform} 题目字段齐全", not miss, f"缺失={miss}" if miss else "")
    miss = [f for f in RANK_FIELDS if f not in ranks[0]]
    check(f"{platform} 排名字段齐全", not miss, f"缺失={miss}" if miss else "")

    # 名次连续性：第一名应为 1，名次应单调不减
    first = ranks[0].get("rank")
    check(f"{platform} 首行名次为 1", first == 1, f"实际={first}")
    seq = [r.get("rank") for r in ranks if isinstance(r.get("rank"), int)]
    check(f"{platform} 名次单调不减", all(a <= b for a, b in zip(seq, seq[1:])),
          f"共 {len(seq)} 条")
    check(f"{platform} 用户标识非空",
          all(r.get("uid") for r in ranks), "uid 全量非空")

    print("  排名字段填充率:", json.dumps(fill_rate(ranks, RANK_FIELDS), ensure_ascii=False))

    if expect_school is not None:
        got = sum(1 for r in ranks if r.get("school"))
        check(f"{platform} school 字段有数据", (got > 0) == expect_school,
              f"非空 {got}/{len(ranks)}")

    sds = [s for r in ranks for s in r.get("score_detail", [])]
    if expect_scoredetail:
        check(f"{platform} score_detail 非空", len(sds) > 0, f"{len(sds)} 条题目记录")
        if sds:
            miss = [f for f in SCORE_FIELDS if f not in sds[0]]
            check(f"{platform} score_detail 字段齐全", not miss, f"缺失={miss}" if miss else "")
            print("  score_detail 填充率:",
                  json.dumps(fill_rate(sds, SCORE_FIELDS), ensure_ascii=False))
            acc = [s for s in sds if s.get("accepted")]
            check(f"{platform} 通过记录含耗时",
                  bool(acc) and sum(1 for s in acc if s.get("reach_time_ms") is not None) > 0,
                  f"AC {len(acc)} 条，有耗时 "
                  f"{sum(1 for s in acc if s.get('reach_time_ms') is not None)} 条")
    else:
        print(f"  score_detail 按设计为空（{platform} 免登录端点不提供每题详情）")

    print("  排名样例:", json.dumps(
        {k: v for k, v in ranks[0].items() if k != "score_detail"},
        ensure_ascii=False)[:400])
    if sds:
        print("  题目明细样例:", json.dumps(sds[0], ensure_ascii=False))


def verify_cf():
    print("\n" + "=" * 26 + " CODEFORCES " + "=" * 26)
    s = CodeforcesScraper()
    contests = s.parse_contests(s.fetch_contests())
    fin = [c for c in contests if c.get("phase") == "FINISHED"]
    check("CF 拉到比赛列表", len(contests) > 1000, f"{len(contests)} 场，已结束 {len(fin)} 场")

    icpc = next((c for c in fin if "Div. 3" in (c["name"] or "")), None)
    cf_style = next((c for c in fin if "Div. 2" in (c["name"] or "")), None)

    for tag, c in [("Div.3(ICPC制)", icpc), ("Div.2(CF制)", cf_style)]:
        if not c:
            continue
        print(f"\n>>> 抓取 {tag}: {c['name']} (id={c['real_contest_id']})")
        t0 = time.time()
        # 每题明细只在 mode="standings" 下才有；默认的 mode="rating" 走
        # ratingChanges，名单更完整但无明细，改由 verify_rated.py 单独验证
        d = s.scrape_contest_detail(c["real_contest_id"], filter_post_contest=True,
                                    mode="standings")
        print(f"    用时 {time.time() - t0:.1f}s")
        audit(f"CF/{tag}", contests, d, expect_school=None)
        if tag.startswith("Div.3"):
            pens = [r["penalty_time_ms"] for r in d["ranks"] if r.get("penalty_time_ms")]
            check("CF ICPC 罚时已换算为毫秒",
                  bool(pens) and max(pens) > 60000,
                  f"最大 {max(pens) if pens else 0} ms")
            fc = [x for r in d["ranks"] for x in r["score_detail"]
                  if x.get("failed_count")]
            check("CF failed_count 可取到（字段名修正验证）", len(fc) > 0,
                  f"{len(fc)} 条含失败次数")
        else:
            check("CF 赛制 full_score 可计算",
                  d["ranks"][0].get("full_score") is not None,
                  f"满分={d['ranks'][0].get('full_score')}")


def verify_at():
    print("\n" + "=" * 27 + " ATCODER " + "=" * 27)
    s = AtCoderScraper()
    contests = s.parse_contests(s.fetch_contests())
    check("AtCoder 拉到比赛列表", len(contests) > 5000, f"{len(contests)} 场")
    now = time.time()
    past = [c for c in contests
            if c.get("start_time") and s._str2ts(c["start_time"]) / 1000 < now - 86400
            and (c["contest_id"] or "").startswith("abc")]
    past.sort(key=lambda x: x["start_time"])
    target = past[-1]
    print(f"\n>>> 抓取: {target['name']} (id={target['real_contest_id']})")
    t0 = time.time()
    d = s.scrape_contest_detail(target["real_contest_id"], filter_post_contest=True)
    print(f"    用时 {time.time() - t0:.1f}s")
    # school 现已按需求置空，学校归属改由注册的平台 ID 绑定
    audit("AtCoder", contests, d, expect_school=False, expect_scoredetail=False)
    if d["ranks"]:
        perf = [r["extra"].get("performance") for r in d["ranks"]
                if r.get("extra", {}).get("performance") is not None]
        check("AtCoder Performance 可取到", len(perf) > 0, f"{len(perf)} 条")
        rated = sum(1 for r in d["ranks"] if r.get("extra", {}).get("is_rated"))
        check("AtCoder is_rated 标记可用", rated > 0, f"rated {rated} 人")
        aff = sum(1 for r in d["ranks"] if r.get("extra", {}).get("affiliation"))
        check("AtCoder Affiliation 已降级到 extra", aff > 0, f"{aff} 人填写")


def verify_nc():
    print("\n" + "=" * 28 + " NOWCODER " + "=" * 27)
    s = NowCoderScraper()
    s.init_session()
    contests = []
    for ym in [time.strftime("%Y-%m"), "2026-07"]:
        contests.extend(s.parse_contests(s.fetch_contests(ym)))
    check("牛客拉到比赛列表", len(contests) > 0, f"{len(contests)} 场")
    now_ms = time.time() * 1000
    ended = [c for c in contests
             if c.get("end_time") and s._str2ts(c["end_time"]) < now_ms
             and c.get("real_contest_id")]
    check("存在已结束比赛可供抓取", len(ended) > 0, f"{len(ended)} 场")

    # 校赛/联赛多为 ICPC 赛制（无 reachTime，靠 acceptedTime 回退）；周赛为 OI 赛制
    weekly = next((c for c in ended if "周赛" in (c["name"] or "")), None)
    icpc = next((c for c in ended
                 if not any(k in (c["name"] or "") for k in ("周赛", "小白月赛", "挑战赛"))),
                None)

    for tag, c in [("ICPC制", icpc), ("周赛(OI制)", weekly)]:
        if not c:
            continue
        print(f"\n>>> 抓取 {tag}: {c['name']} (id={c['real_contest_id']})")
        t0 = time.time()
        d = s.scrape_contest_detail(c["real_contest_id"], max_rank_pages=4,
                                    filter_post_contest=True)
        print(f"    用时 {time.time() - t0:.1f}s（限 4 页，仅验证契约）")
        audit(f"牛客/{tag}", contests, d, expect_school=None)
        acc = [x for r in d["ranks"] for x in r["score_detail"] if x.get("accepted")]
        with_t = [x for x in acc if x.get("reach_time_ms") is not None]
        check(f"牛客/{tag} AC 记录含相对耗时（reachTime 回退验证）",
              len(acc) > 0 and len(with_t) == len(acc),
              f"{len(with_t)}/{len(acc)}")


def verify_pagination():
    """单独验证牛客按 pageCount 自动翻页能抓完整场"""
    print("\n" + "=" * 24 + " 牛客完整翻页验证 " + "=" * 24)
    s = NowCoderScraper()
    s.init_session()
    contests = s.parse_contests(s.fetch_contests(time.strftime("%Y-%m")))
    now_ms = time.time() * 1000
    ended = [c for c in contests
             if c.get("end_time") and s._str2ts(c["end_time"]) < now_ms
             and c.get("real_contest_id")]
    if not ended:
        print("  当月无已结束比赛，跳过")
        return
    c = ended[0]
    print(f">>> 完整抓取: {c['name']} (id={c['real_contest_id']})")
    t0 = time.time()
    info = s.fetch_all_ranks(c["real_contest_id"])
    total = (info.get("basic_info") or {}).get("rankCount")
    got = len(info.get("rank_data", []))
    print(f"    用时 {time.time() - t0:.1f}s")
    check("牛客翻页抓全（rank_data 数 == basicInfo.rankCount）",
          total is not None and got == total, f"{got}/{total}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "cf"):
        verify_cf()
    if which in ("all", "at"):
        verify_at()
    if which in ("all", "nc"):
        verify_nc()
    if which in ("all", "page"):
        verify_pagination()

    print("\n" + "=" * 30 + " 汇总 " + "=" * 30)
    ok = sum(1 for r in _results if r[0] == PASS)
    bad = [r for r in _results if r[0] == FAIL]
    for _, label, note in bad:
        print(f"  [FAIL] {label}  {note}")
    print(f"\n通过 {ok}/{len(_results)}，失败 {len(bad)}")
    sys.exit(1 if bad else 0)
