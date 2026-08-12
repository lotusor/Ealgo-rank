#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rated / 付费过滤逻辑的联网回归验证。

用法：
    python verify_rated.py [cf|at|nc|all]

对每个平台取近期一批比赛，跑一遍 check_rated / filter_contests，
打印判定明细并断言若干已知事实（如 April Fools 必须 unrated、
2026 牛客暑期多校必须被判为付费）。
"""

import sys

from atcoder_scraper import AtCoderScraper
from cf_scraper import CodeforcesScraper
from nowcoder_scraper import NowCoderScraper

FAILED = []


def check(cond, msg):
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {msg}")
    if not cond:
        FAILED.append(msg)
    return cond


def hr(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


# ---------------- Codeforces ----------------
def verify_cf():
    hr("Codeforces：rated 判定")
    s = CodeforcesScraper()
    contests = s.parse_contests(s.fetch_contests())
    finished = [c for c in contests if c.get("phase") == "FINISHED"]
    print(f"  已结束比赛 {len(finished)} 场，取最近 8 场判定")

    sample = finished[:8]
    for c in sample:
        flags = s.check_rated(c)
        c.update(flags)
        print(f"    {c['real_contest_id']:>6} rated={str(c['is_rated']):5s} "
              f"paid={c['is_paid']}  {c['name'][:42]}  ({c['rated_comment'][:44]})")

    check(all(c.get("is_paid") is False for c in sample),
          "CF 全部比赛 is_paid=False")
    check(any(c.get("is_rated") for c in sample),
          "样本中至少有一场 rated")

    # 已知事实：2216 是 Unrated Round，2248 是正常 Div.2
    known_unrated = s.check_rated({"real_contest_id": 2216, "phase": "FINISHED"})
    known_rated = s.check_rated({"real_contest_id": 2248, "phase": "FINISHED"})
    print(f"    2216 (Unrated Round) -> is_rated={known_unrated['is_rated']}")
    print(f"    2248 (Div.2)         -> is_rated={known_rated['is_rated']}")
    check(known_unrated["is_rated"] is False, "2216 Unrated Round 被正确判为非 rated")
    check(known_rated["is_rated"] is True, "2248 Div.2 被正确判为 rated")

    # 未结束比赛不应被误判
    pend = s.check_rated({"real_contest_id": 9999, "phase": "BEFORE"})
    check(pend["is_rated"] is None, "未开始比赛 is_rated=None（不误判为 unrated）")

    # ratingChanges 名单比 standings 完整
    ok, rc, _ = s.fetch_rating_changes(2248)
    rows = s.parse_rating_changes(rc)
    print(f"    2248 ratingChanges 名单 {len(rows)} 人")
    check(len(rows) > 13000, f"2248 名单完整（{len(rows)} 人 > 13000）")
    check(rows[0]["school"] is None, "CF 排名不再携带学校字段")
    check(rows[0]["extra"]["delta"] is not None, "rating delta 已计算")

    # 按 handle 精准补明细
    detail = s.parse_user_submissions(s.fetch_user_contest_status(2248, "Zhao05"))
    print(f"    Zhao05 每题明细: {[(d['problem'], d['accepted']) for d in detail]}")
    check(len(detail) >= 2, "standings 缺失的用户可通过 contest.status 补齐明细")
    return s


# ---------------- AtCoder ----------------
def verify_at():
    hr("AtCoder：rated 判定")
    s = AtCoderScraper()
    contests = s.parse_contests(s.fetch_contests())
    print(f"  全站比赛 {len(contests)} 场")

    for c in contests:
        c.update(s.check_rated(c))
    rated = [c for c in contests if c["is_rated"]]
    unrated = [c for c in contests if not c["is_rated"]]
    print(f"  rated={len(rated)}  unrated={len(unrated)}")

    print("  rated 样例:")
    for c in rated[:4]:
        print(f"    {c['contest_id']:<16s} {c['rated_comment']:<22s} {c['name'][:38]}")
    print("  unrated 样例:")
    for c in unrated[:4]:
        print(f"    {c['contest_id']:<16s} {c['rated_comment']:<22s} {c['name'][:38]}")

    check(len(rated) > 0 and len(unrated) > 0, "rated / unrated 均有命中")
    check(all(c["is_paid"] is False for c in contests), "AtCoder 全部 is_paid=False")
    check(all(c["rate_change"] != "-" for c in rated), "rated 集合内无 rate_change='-'")
    check(all((c["rate_change"] or "-") == "-" for c in unrated),
          "unrated 集合全部 rate_change='-'")

    # 过滤后取一场实际抓排名，确认 school 已清空
    target = next((c for c in rated
                   if c["contest_id"].startswith("abc")
                   and c["start_time"] and c["start_time"] < "2026-07"), None)
    if target:
        print(f"  抽查 {target['contest_id']} 的排名字段")
        info = s.fetch_all_ranks(target["contest_id"])
        ranks = s.parse_ranks(info)
        if ranks:
            r = ranks[0]
            print(f"    第1名 uid={r['uid']} school={r['school']} "
                  f"affiliation={r['extra'].get('affiliation')}")
            check(all(x["school"] is None for x in ranks[:500]),
                  "AtCoder 排名 school 已置空（不再用 Affiliation 绑定学校）")
            check("affiliation" in r["extra"], "Affiliation 已降级到 extra")
    return s


# ---------------- 牛客 ----------------
def verify_nc():
    hr("牛客：rated / 付费判定")
    s = NowCoderScraper()
    s.init_session()

    cases = [
        (138240, "牛客周赛 Round 155", True, False),
        (137264, "牛客小白月赛135", True, False),
        (137418, "牛客挑战赛90", True, False),
        (82612, "牛客练习赛125", True, False),
        (133876, "2026牛客暑期多校训练营1", True, True),    # rated 但收费
        (23106, "2022牛客寒假算法基础集训营1", True, True),  # rated 但收费
        (137532, "金山杯武汉理工校赛", False, False),
        (137658, "河南萌新联赛(河南工业大学)", False, False),
    ]
    for cid, name, exp_rated, exp_paid in cases:
        f = s.check_rated({"real_contest_id": cid})
        print(f"    {cid:>6} rated={str(f['is_rated']):5s} paid={str(f['is_paid']):5s} "
              f"{name[:26]:<28s} {f['rated_comment'][:50]}")
        check(f["is_rated"] == exp_rated, f"{name} is_rated={exp_rated}")
        check(f["is_paid"] == exp_paid, f"{name} is_paid={exp_paid}")

    # 过滤器整体行为：付费的多校/寒假营必须被剔除
    metas = [{"real_contest_id": cid, "name": nm} for cid, nm, _, _ in cases]
    kept = s.filter_contests(metas, rated_only=True, exclude_paid=True)
    kept_ids = {c["real_contest_id"] for c in kept}
    print(f"  过滤后保留 {sorted(kept_ids)}")
    check(kept_ids == {138240, 137264, 137418, 82612},
          "只保留免费的官方 rated 赛（周赛/小白月赛/挑战赛/练习赛）")

    # 排名字段：school 应已置空
    info = s.fetch_all_ranks(138240, max_pages=1)
    ranks = s.parse_ranks(info)
    if ranks:
        r = ranks[0]
        print(f"    第1名 uid={r['uid']} school={r['school']} "
              f"profile_school={r['extra'].get('profile_school')}")
        check(all(x["school"] is None for x in ranks),
              "牛客排名 school 已置空（不再用榜单学校绑定）")
        check("profile_school" in r["extra"], "榜单学校已降级到 extra")

    # ---- 作弊账号识别 ----
    hr("牛客：作弊账号识别")
    # 离线用例，覆盖标记文案的各种写法
    offline = [
        ("【已被标记为作弊】张三", True, "张三"),
        ("[已被标记为作弊]abc", True, "abc"),
        ("【该用户已被标记为作弊】x", True, "x"),
        ("【已被平台标记为作弊】y", True, "y"),
        ("【已被标记为作弊，成绩无效】z", True, "z"),
        ("正常昵称", False, "正常昵称"),
        ("【大佬】李四", False, "【大佬】李四"),   # 不能误伤带方括号的普通昵称
    ]
    ok = True
    for raw, exp_flag, exp_name in offline:
        got_flag, got_name, _ = s.detect_cheater(raw)
        if got_flag != exp_flag or got_name != exp_name:
            ok = False
            print(f"    误判: {raw!r} -> ({got_flag}, {got_name!r})")
    check(ok, f"作弊标记正则覆盖 {len(offline)} 种写法且不误伤普通昵称")

    # 联网用例：周赛榜单实测存在被标记账号
    ranks = s.parse_ranks(s.fetch_all_ranks(138240, max_pages=4))
    cheaters = [x for x in ranks if x["is_cheater"]]
    print(f"    Round 155 取样 {len(ranks)} 条，检出作弊 {len(cheaters)} 条")
    for x in cheaters[:3]:
        print(f"      #{x['rank']} uid={x['uid']} {x['user_name']!r} "
              f"<- {x['extra']['raw_user_name']!r}")
    check(all("is_cheater" in x for x in ranks), "每条排名都带 is_cheater 字段")
    check(len(cheaters) > 0, "真实榜单中检出被平台标记的作弊账号")
    check(all("标记为作弊" not in (x["user_name"] or "") for x in ranks),
          "user_name 已剥离作弊标记前缀")
    check(all(x["extra"].get("raw_user_name") for x in cheaters),
          "作弊记录保留原始昵称供审计")

    # exclude_cheaters=True 时应直接丢弃
    pruned = s.parse_ranks(s.fetch_all_ranks(138240, max_pages=4),
                           exclude_cheaters=True)
    check(len(pruned) == len(ranks) - len(cheaters),
          f"exclude_cheaters=True 精确剔除 {len(cheaters)} 条")
    check(not any(x["is_cheater"] for x in pruned), "剔除后无残留作弊记录")
    return s


def main():
    which = (sys.argv[1] if len(sys.argv) > 1 else "all").lower()
    if which in ("cf", "all"):
        verify_cf()
    if which in ("at", "atcoder", "all"):
        verify_at()
    if which in ("nc", "nowcoder", "all"):
        verify_nc()

    hr("汇总")
    if FAILED:
        print(f"  {len(FAILED)} 项未通过：")
        for m in FAILED:
            print(f"    - {m}")
        sys.exit(1)
    print("  全部断言通过")


if __name__ == "__main__":
    main()
