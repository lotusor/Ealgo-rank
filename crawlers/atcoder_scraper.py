#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AtCoder 比赛信息与用户排名爬虫
- 比赛列表来自 AtCoder Problems 非官方 API（kenkoooo），遵守请求间隔 >1s 的礼貌要求
- 题目列表来自 kenkoooo 的 contest-problem.json + problems.json（全局拉取一次后缓存）
- 比赛排名来自 AtCoder 官方 results 端点（/contests/{id}/results/json），免登录可访问，
  含名次 Place、所属机构 Affiliation、表现分 Performance、赛前/赛后 Rating
- 支持按月份过滤、批量抓取

说明：官方 /standings/json 需要登录（未登录会 302 跳转 /login），因此不可用于无人值守
采集；results 端点不含每题提交详情，故 score_detail 为空列表。若后续确需每题详情，
可改用 kenkoooo 的 /v3/from/{unix_second} 提交流按比赛时间窗回放，成本较高。

【只收录 rated 比赛】
  判定依据：contests.json 的 rate_change 字段
    "-"                -> unrated（全站 6276 场中 5477 场属此类）
    "All" / "- ~ 1999" -> rated，字符串同时给出了受影响的 rating 区间
  results/json 每行还带 IsRated，可用于交叉校验个人是否被计分。
  AtCoder 无付费比赛，is_paid 恒为 False。
"""

import json
import random
import time
from datetime import datetime
from pathlib import Path

import requests


class AtCoderScraper:
    """AtCoder 比赛信息爬虫"""

    def __init__(self, delay=(1.1, 2.0), timeout=60):
        # kenkoooo 要求请求间隔 >1 秒，取 1.1~2.0s
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            "Connection": "keep-alive",
        })
        self.base_list = "https://kenkoooo.com/atcoder/resources"
        self.base_atcoder = "https://atcoder.jp"
        self._problem_index = None  # {contest_id: [problem, ...]}

    # ---------- 底层请求 ----------
    def _sleep(self):
        time.sleep(random.uniform(*self.delay))

    def _get(self, url, **kwargs):
        self._sleep()
        resp = self.session.get(url, timeout=self.timeout, **kwargs)
        resp.raise_for_status()
        return resp

    @staticmethod
    def _ts2str(ts):
        """秒级时间戳 → 字符串"""
        if not ts:
            return None
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _str2ts(s):
        """字符串 → 毫秒级时间戳（与 _ts2str 格式对应）"""
        if not s:
            return None
        try:
            return int(datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
        except Exception:
            return None

    # ---------- 比赛列表 ----------
    def fetch_contests(self):
        """从 AtCoder Problems 拉取全部比赛列表"""
        url = f"{self.base_list}/contests.json"
        contests = self._get(url).json()
        print(f"[fetch_contests] 共 {len(contests)} 条比赛记录")
        return contests

    @staticmethod
    def parse_contests(contests):
        """解析比赛列表，提取标准化字段"""
        results = []
        for c in contests:
            cid = c.get("id")
            start = c.get("start_epoch_second")
            dur = c.get("duration_second") or 0
            results.append({
                "contest_id": cid,
                "real_contest_id": cid,
                "name": c.get("title"),
                "oj": "AtCoder",
                "link": f"https://atcoder.jp/contests/{cid}",
                "start_time": AtCoderScraper._ts2str(start),
                "end_time": AtCoderScraper._ts2str(start + dur if start else None),
                "duration_minutes": dur // 60,
                "rate_change": c.get("rate_change"),
            })
        return results

    # ---------- rated / 付费判定 ----------
    @staticmethod
    def check_rated(contest_meta):
        """
        统一契约方法：判定一场比赛是否 rated / 是否付费。
        rate_change 为 "-" 或空即 unrated；其余（"All"、"- ~ 1999" 等）为 rated。
        """
        rc = (contest_meta.get("rate_change") or "").strip()
        is_rated = bool(rc) and rc != "-"
        return {
            "is_rated": is_rated,
            "is_paid": False,                     # AtCoder 无付费比赛
            "rated_source": "contests.json:rate_change",
            "rated_comment": f"rate_change={rc or '(空)'}",
        }

    def filter_contests(self, contests, rated_only=True, exclude_paid=True):
        """按 rated / 付费规则筛选比赛，并把判定结果写回比赛字段"""
        kept = []
        for c in contests:
            c.update(self.check_rated(c))
            if rated_only and not c.get("is_rated"):
                print(f"[filter] 排除非 rated: {c['name']} ({c.get('rated_comment')})")
                continue
            if exclude_paid and c.get("is_paid"):
                print(f"[filter] 排除付费赛: {c['name']}")
                continue
            kept.append(c)
        print(f"[filter] rated 且免费的比赛 {len(kept)}/{len(contests)} 场")
        return kept

    # ---------- 题目列表 ----------
    def _build_problem_index(self):
        """
        拉取全站题目与「比赛-题目」映射并建索引（各约 1MB / 3MB，仅拉一次）。
        官方 standings 需登录，题面信息只能从这里取。
        """
        if self._problem_index is not None:
            return self._problem_index
        problems = self._get(f"{self.base_list}/problems.json").json()
        pmap = {p.get("id"): p for p in problems}
        pairs = self._get(f"{self.base_list}/contest-problem.json").json()
        index = {}
        for item in pairs:
            cid = item.get("contest_id")
            pid = item.get("problem_id")
            meta = pmap.get(pid, {})
            index.setdefault(cid, []).append({
                "id": pid,
                "contest_id": cid,
                "problem_index": item.get("problem_index") or meta.get("problem_index"),
                "name": meta.get("name"),
                "title": meta.get("title"),
            })
        for cid in index:
            index[cid].sort(key=lambda x: (x.get("problem_index") or ""))
        self._problem_index = index
        print(f"[_build_problem_index] 已建索引：{len(pmap)} 题 / {len(index)} 场比赛")
        return index

    def fetch_problem_list(self, contest_id):
        """取某场比赛的题目列表"""
        index = self._build_problem_index()
        problems = index.get(contest_id, [])
        print(f"[fetch_problem_list] {contest_id} 共 {len(problems)} 题")
        return problems

    @staticmethod
    def parse_problems(problems):
        return [{
            "index": p.get("problem_index"),
            "title": p.get("name"),
            "problem_id": p.get("id"),
            "score": None,
            "total_score": None,
            "submit_count": None,
            "accepted_count": None,
            "submit_person_count": None,
        } for p in problems]

    # ---------- 排名数据 ----------
    def fetch_rank_page(self, contest_id, page=1):
        """
        官方 results 端点单次返回全量（无分页），page 仅为保持接口一致。
        比赛未产生成绩（如尚未结束、或非 rated 无结果）时返回空列表。
        """
        url = f"{self.base_atcoder}/contests/{contest_id}/results/json"
        try:
            resp = self._get(url)
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            print(f"[fetch_rank_page] {contest_id} 获取失败: HTTP {code}")
            return None
        if "json" not in (resp.headers.get("Content-Type") or ""):
            print(f"[fetch_rank_page] {contest_id} 非 JSON 响应，可能需要登录")
            return None
        return resp.json()

    def fetch_all_ranks(self, contest_id, max_pages=50):
        """官方 results 单次返回全量，max_pages 仅为保持接口一致"""
        rows = self.fetch_rank_page(contest_id, page=1)
        if not rows:
            return {"problem_data": [], "rank_data": []}
        print(f"[fetch_all_ranks] {contest_id} 获取 {len(rows)} 条")
        return {
            "problem_data": self._build_problem_index().get(contest_id, []),
            "rank_data": rows,
        }

    @staticmethod
    def parse_ranks(rank_info, filter_post_contest=False):
        """
        解析并简化排名数据。
        AtCoder results 仅含正式参赛者，filter_post_contest 保留仅为接口一致。
        每题提交详情官方免登录端点不提供，score_detail 恒为空列表。

        注意：Affiliation 是用户自填的所属机构（学校/公司），写法极不统一且大量为空
        （abc469 实测 12876 人中仅 3601 人填写），不作为学校归属依据，
        只放进 extra 供人工核对。学校归属一律由注册时绑定的平台 ID 决定。
        """
        ranks = []
        for r in rank_info.get("rank_data", []):
            affiliation = (r.get("Affiliation") or "").strip() or None
            ranks.append({
                "rank": r.get("Place"),
                "uid": r.get("UserScreenName"),
                "user_name": r.get("UserName") or r.get("UserScreenName"),
                "school": None,   # 不从比赛数据推断学校，见上方说明
                "team": None,
                "accepted_count": None,   # results 端点不含题目通过数
                "total_score": None,      # results 端点不含得分
                "full_score": None,
                "penalty_time_ms": None,
                "color_level": None,
                "post_contest_append": False,
                # AtCoder 判定作弊的账号会被 unrate（IsRated=false），
                # 榜单不带作弊文案。字段保留仅为三平台入库契约一致。
                "is_cheater": False,
                "score_detail": [],
                "extra": {
                    "affiliation": affiliation,   # 用户自填，仅供参考
                    "performance": r.get("Performance"),
                    "old_rating": r.get("OldRating"),
                    "new_rating": r.get("NewRating"),
                    "rating": r.get("Rating"),
                    "is_rated": r.get("IsRated"),
                    "country": r.get("Country"),
                    "competitions": r.get("Competitions"),
                    "atcoder_rank": r.get("AtCoderRank"),
                },
            })
        return ranks

    # ---------- 批量抓取 ----------
    def scrape_contest_detail(self, contest_id, max_rank_pages=50,
                              filter_post_contest=False):
        """抓取单场比赛的题目与全部有效排名"""
        problems = self.parse_problems(self.fetch_problem_list(contest_id))
        rank_info = self.fetch_all_ranks(contest_id, max_pages=max_rank_pages)
        ranks = self.parse_ranks(rank_info, filter_post_contest=filter_post_contest)
        valid_count = sum(1 for r in ranks if not r.get("post_contest_append"))
        return {
            "problems": problems,
            "ranks": ranks,
            "rank_count": len(ranks),
            "valid_rank_count": valid_count,
            "crawled_at": datetime.now().isoformat(),
        }

    def run(self, months=None, output_dir=None, max_rank_pages=50,
            skip_future=True, filter_post_contest=True,
            rated_only=True, exclude_paid=True):
        """
        入口：抓取比赛列表，并抓取每场比赛的全部有效排名。
        rated_only=True   只收录 rate_change != '-' 的比赛（默认）
        exclude_paid=True 排除付费比赛（AtCoder 无付费赛，占位保持三平台一致）
        """
        if months is None:
            months = [datetime.now().strftime("%Y-%m")]

        out = (Path(output_dir) if output_dir
               else Path(__file__).resolve().parent / "data" / "atcoder")
        out.mkdir(parents=True, exist_ok=True)

        # 1. 比赛列表（客户端按月份过滤）
        all_contests = self.parse_contests(self.fetch_contests())
        if months:
            all_contests = [
                c for c in all_contests
                if c.get("start_time") and c["start_time"][:7] in months
            ]

        # 2. 剔除未开始的比赛，再做 rated / 付费过滤
        now_ts = int(time.time() * 1000)
        if skip_future:
            pending = []
            for c in all_contests:
                start_ts = self._str2ts(c.get("start_time"))
                if start_ts and start_ts > now_ts:
                    print(f"[run] 跳过未开始比赛: {c['name']} ({c['start_time']})")
                    continue
                pending.append(c)
            all_contests = pending

        if rated_only or exclude_paid:
            all_contests = self.filter_contests(
                all_contests, rated_only=rated_only, exclude_paid=exclude_paid)

        list_path = out / "contest_list.json"
        with open(list_path, "w", encoding="utf-8") as f:
            json.dump(all_contests, f, ensure_ascii=False, indent=2)
        print(f"[run] 已保存 {len(all_contests)} 条比赛列表 -> {list_path}")

        # 3. 每场比赛详情
        details = {}
        for c in all_contests:
            rid = c.get("real_contest_id")
            if not rid:
                continue

            print(f"\n[run] 正在抓取比赛: {c['name']} (id={rid})")
            try:
                detail = self.scrape_contest_detail(
                    rid,
                    max_rank_pages=max_rank_pages,
                    filter_post_contest=filter_post_contest,
                )
                detail["contest_meta"] = c
                # 题目与排名皆空说明比赛尚未就绪，不保存空详情
                if not detail.get("problems") and not detail.get("ranks"):
                    print(f"[run] 比赛 {rid} 暂无题目/排名数据，跳过保存")
                    continue
                details[rid] = detail
                detail_path = out / f"contest_{rid}.json"
                with open(detail_path, "w", encoding="utf-8") as f:
                    json.dump(detail, f, ensure_ascii=False, indent=2)
                print(f"[run] 比赛 {rid} 有效排名: {detail['valid_rank_count']} 条")
            except Exception as e:
                print(f"[run] 抓取比赛 {rid} 失败: {e}")

        summary_path = out / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump({
                "months": months,
                "rated_only": rated_only,
                "exclude_paid": exclude_paid,
                "contest_count": len(all_contests),
                "detail_count": len(details),
                "contests": all_contests,
            }, f, ensure_ascii=False, indent=2)
        print(f"\n[run] 完成，共抓取 {len(details)}/{len(all_contests)} 场比赛详情 -> {out}")
        return details


if __name__ == "__main__":
    scraper = AtCoderScraper()
    # 默认输出到脚本同级 data/atcoder/，抓取当月比赛
    # 需要多月份时传入 months=["2026-07", "2026-08", "2026-09"]
    scraper.run()
