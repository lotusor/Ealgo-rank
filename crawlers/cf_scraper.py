#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Codeforces 比赛信息与用户排名爬虫
- 使用官方公开 API（无需登录、无需签名），遵守 1 次/2 秒频率限制
- 抓取比赛列表、比赛题目、实时排名（含每题提交详情）
- 支持按月份过滤、批量抓取

【只收录 rated 比赛】
  权威判定：contest.ratingChanges?contestId=X
    status=OK      -> rated（返回全量参赛者的 rank 与 rating 变化）
    status=FAILED  -> unrated（如 April Fools、Unrated Round、ICPC 镜像赛）
  Codeforces 无付费比赛，is_paid 恒为 False。

【重要：匿名 standings 会丢人，大场次不可信】
  实测同一场比赛：
    2248 Div.2  standings 9190  vs ratingChanges 13317
    2244 Div.3  standings 12173 vs ratingChanges 20340
    2150 小场    standings 961   vs ratingChanges 961（一致）
  standings 是 ratingChanges 的严格子集（没有任何人只出现在 standings 里）。
  因此 rated 场次一律以 ratingChanges 为全量名单基准；
  需要某人的每题明细时用 contest.status?contestId=X&handle=Y 精准补齐。
"""

import json
import random
import time
from datetime import datetime
from pathlib import Path

import requests


class CodeforcesScraper:
    """Codeforces 比赛信息爬虫"""

    def __init__(self, delay=(2.1, 3.0), timeout=90):
        # 官方硬性限速：1 次/2 秒，间隔取 2.1~3.0s 留出余量
        # 单场 standings 可达 10MB（Div.3 一万两千行），timeout 需放宽
        self.delay = delay
        self.timeout = timeout
        self._standings_cache = {}
        self._rating_cache = {}
        self._problemset_index = None
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
        self.base = "https://codeforces.com/api"

    # ---------- 底层请求 ----------
    def _sleep(self):
        time.sleep(random.uniform(*self.delay))

    def _get(self, url, **kwargs):
        self._sleep()
        resp = self.session.get(url, timeout=self.timeout, **kwargs)
        resp.raise_for_status()
        return resp

    def _get_soft(self, url, **kwargs):
        """容错请求：不抛异常，直接返回官方 JSON（含 status=FAILED 的情形）"""
        self._sleep()
        try:
            resp = self.session.get(url, timeout=self.timeout, **kwargs)
            return resp.json()
        except Exception as e:
            return {"status": "EXCEPTION", "comment": f"{type(e).__name__}: {e}"}

    @staticmethod
    def _check(data):
        """校验官方 API 返回，status != OK 时抛错"""
        if data.get("status") != "OK":
            raise RuntimeError(f"Codeforces API 返回错误: {data.get('comment')}")
        return data.get("result")

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
        """抓取全部常规比赛列表（gym=False）"""
        ts = int(time.time() * 1000)
        url = f"{self.base}/contest.list?gym=false&_={ts}"
        data = self._get(url).json()
        contests = self._check(data)
        print(f"[fetch_contests] 共 {len(contests)} 条比赛记录")
        return contests

    @staticmethod
    def parse_contests(contests):
        """解析比赛列表，提取标准化字段"""
        results = []
        for c in contests:
            cid = c.get("id")
            start = c.get("startTimeSeconds")
            dur = c.get("durationSeconds") or 0
            results.append({
                "contest_id": cid,
                "real_contest_id": cid,
                "name": c.get("name"),
                "oj": "Codeforces",
                "link": f"https://codeforces.com/contest/{cid}",
                "start_time": CodeforcesScraper._ts2str(start),
                "end_time": CodeforcesScraper._ts2str(start + dur if start else None),
                "duration_minutes": dur // 60,
                "phase": c.get("phase"),
                "type": c.get("type"),
            })
        return results

    # ---------- rated / 付费判定 ----------
    def fetch_rating_changes(self, contest_id, use_cache=True):
        """
        拉取该场的 rating 变化。这是判定 rated 的权威依据，
        同时也是该场【全量参赛者】的可信名单（比 standings 更完整）。
        返回 (ok: bool, result: list|None, comment: str)
        """
        if use_cache and contest_id in self._rating_cache:
            return self._rating_cache[contest_id]
        url = f"{self.base}/contest.ratingChanges?contestId={contest_id}"
        data = self._get_soft(url)
        if data.get("status") == "OK":
            item = (True, data.get("result") or [], "")
        else:
            item = (False, None, str(data.get("comment") or "")[:120])
        if use_cache:
            self._rating_cache[contest_id] = item
        return item

    def check_rated(self, contest_meta):
        """
        统一契约方法：判定一场比赛是否 rated / 是否付费。
        返回 dict(is_rated, is_paid, rated_source, rated_comment)
        注意：比赛尚未结束或 rating 尚未结算时同样会返回 FAILED，
        因此调用方需先用 phase == "FINISHED" 过滤，避免把新赛误判为 unrated。
        """
        cid = contest_meta.get("real_contest_id") or contest_meta.get("contest_id")
        phase = contest_meta.get("phase")
        if phase and phase != "FINISHED":
            return {"is_rated": None, "is_paid": False,
                    "rated_source": "phase", "rated_comment": f"phase={phase}，尚未结算"}
        ok, result, comment = self.fetch_rating_changes(cid)
        return {
            "is_rated": bool(ok and result),
            "is_paid": False,                       # Codeforces 无付费比赛
            "rated_source": "contest.ratingChanges",
            "rated_comment": comment if not ok else f"{len(result)} 条 rating 变化",
        }

    @staticmethod
    def parse_rating_changes(rating_changes):
        """
        把 ratingChanges 转成与 parse_ranks 同构的精简排名（无每题明细）。
        大场次下这是唯一完整的参赛名单，缺失的每题明细可按需用
        fetch_user_contest_status 补齐。
        """
        rows = []
        for x in rating_changes or []:
            old, new = x.get("oldRating"), x.get("newRating")
            rows.append({
                "rank": x.get("rank"),
                "uid": x.get("handle"),
                "user_name": x.get("handle"),
                "school": None,          # 学校不从比赛数据采集，由注册ID绑定
                "team": None,
                "accepted_count": None,
                "total_score": None,
                "full_score": None,
                "penalty_time_ms": None,
                "color_level": None,
                "post_contest_append": False,
                # CF 判定作弊的选手会被移出 ratingChanges，本列表天然不含作弊者。
                # 保留字段是为了让三平台入库契约一致。
                "is_cheater": False,
                "score_detail": [],
                "extra": {
                    "source": "ratingChanges",
                    "old_rating": old,
                    "new_rating": new,
                    "delta": (new - old) if (old is not None and new is not None) else None,
                    "rating_update_time": x.get("ratingUpdateTimeSeconds"),
                },
            })
        return rows

    # ---------- 按 handle 精准取数 ----------
    def fetch_user_contest_status(self, contest_id, handle, count=200):
        """
        取某个用户在某场比赛的全部提交。用于补齐 standings 里被丢掉的用户。
        实测该接口不受 standings 的匿名限制，可带 from/count 参数。
        """
        url = (f"{self.base}/contest.status?contestId={contest_id}"
               f"&handle={handle}&from=1&count={count}")
        data = self._get_soft(url)
        if data.get("status") != "OK":
            return None
        return data.get("result") or []

    @staticmethod
    def parse_user_submissions(submissions, participant_type="CONTESTANT"):
        """
        由个人提交流重建每题明细，字段与 parse_ranks 的 score_detail 对齐。
        CF 制的动态分值无法由提交流还原，score 统一留空，
        排名与积分以 ratingChanges 的 rank / delta 为准。
        """
        by_problem = {}
        for s in submissions or []:
            if s.get("author", {}).get("participantType") != participant_type:
                continue
            prob = s.get("problem") or {}
            idx = prob.get("index")
            if not idx:
                continue
            slot = by_problem.setdefault(idx, {
                "problem": idx,
                "problem_id": f"{prob.get('contestId')}-{idx}",
                "accepted": False,
                "score": None,
                "failed_count": 0,
                "reach_time_ms": None,
                "first_blood": None,
                "post_contest_score": None,
            })
            rel = s.get("relativeTimeSeconds")
            if s.get("verdict") == "OK":
                if not slot["accepted"]:
                    slot["accepted"] = True
                    slot["reach_time_ms"] = rel * 1000 if rel is not None else None
            elif not slot["accepted"] and s.get("verdict") not in ("COMPILATION_ERROR", None):
                slot["failed_count"] += 1
        return sorted(by_problem.values(), key=lambda x: x["problem"])

    # ---------- 题目列表 ----------
    def fetch_problemset_index(self, use_cache=True):
        """
        一次性拉取全站题库并按 contestId 建索引。
        用于在【不下载 9MB standings】的前提下拿到某场比赛的题目列表。
        """
        if use_cache and self._problemset_index is not None:
            return self._problemset_index
        data = self._get_soft(f"{self.base}/problemset.problems")
        index = {}
        if data.get("status") == "OK":
            for p in (data.get("result") or {}).get("problems", []):
                index.setdefault(p.get("contestId"), []).append(p)
            for v in index.values():
                v.sort(key=lambda x: x.get("index") or "")
        print(f"[fetch_problemset_index] 覆盖 {len(index)} 场比赛的题目")
        if use_cache:
            self._problemset_index = index
        return index

    def fetch_standings(self, contest_id, use_cache=True):
        """
        获取整场公开排名。
        注意：匿名模式只允许 contestId 一个查询参数，带 from/count 会被拒
        （实测返回 400: "available only via anonymous GET requests with no
        extra parameters"），因此单次即返回完整榜单，无需也无法翻页。
        单场响应体积较大（Div.2 约 7MB / Div.3 约 9MB），故做会话内缓存，
        避免题目列表与排名两次调用重复下载。
        """
        if use_cache and contest_id in self._standings_cache:
            return self._standings_cache[contest_id]
        url = f"{self.base}/contest.standings?contestId={contest_id}"
        data = self._get(url).json()
        result = self._check(data)
        if use_cache:
            self._standings_cache[contest_id] = result
        return result

    def clear_cache(self, contest_id=None):
        """释放 standings / ratingChanges 缓存，避免批量抓取时内存堆积"""
        if contest_id is None:
            self._standings_cache.clear()
            self._rating_cache.clear()
        else:
            self._standings_cache.pop(contest_id, None)
            self._rating_cache.pop(contest_id, None)

    def fetch_problem_list(self, contest_id):
        """从 standings 响应中提取题目列表"""
        result = self.fetch_standings(contest_id)
        problems = result.get("problems", [])
        print(f"[fetch_problem_list] {contest_id} 共 {len(problems)} 题")
        return problems

    @staticmethod
    def parse_problems(problems):
        return [{
            "index": p.get("index"),
            "title": p.get("name"),
            "problem_id": f"{p.get('contestId')}-{p.get('index')}",
            "score": p.get("points"),
            "total_score": None,
            "submit_count": None,
            "accepted_count": None,
            "submit_person_count": None,
        } for p in problems]

    # ---------- 排名数据 ----------
    def fetch_all_ranks(self, contest_id, max_pages=50):
        """公开榜单次返回全量，max_pages 仅为保持接口一致"""
        result = self.fetch_standings(contest_id)
        return {
            "contest_info": result.get("contest", {}),
            "problem_data": result.get("problems", []),
            "rank_data": result.get("rows", []),
        }

    @staticmethod
    def parse_ranks(rank_info, filter_post_contest=False):
        """
        解析并简化排名数据。
        filter_post_contest=True 时过滤掉非正式参赛者（rank<=0 或非 CONTESTANT）。
        注：匿名 standings 只返回正式参赛者（实测 participantType 全为 CONTESTANT、
        无 rank<=0 的行），practice / virtual 提交不在其中，该过滤实际不会命中，
        保留仅为与其他平台接口语义一致。
        """
        problem_order = rank_info.get("problem_data", [])
        # 赛制决定罚时语义：ICPC 制 penalty 为分钟数；CF 制按分数衰减、penalty 恒 0 无意义
        contest_type = (rank_info.get("contest_info") or {}).get("type")
        # ICPC 制题目无 points 字段，满分不可计算
        problem_points = [p.get("points") for p in problem_order]
        full_score = (sum(problem_points)
                      if problem_points and all(x is not None for x in problem_points)
                      else None)

        ranks = []
        for r in rank_info.get("rank_data", []):
            party = r.get("party", {})
            ptype = party.get("participantType")
            is_post = bool(r.get("rank", 0) <= 0) or (ptype != "CONTESTANT")
            if filter_post_contest and is_post:
                continue

            members = party.get("members") or party.get("contestantMembers") or []
            handle = members[0].get("handle") if members else None
            prs = r.get("problemResults", [])

            score_detail = []
            for p, pr in zip(problem_order, prs):
                best_sec = pr.get("bestSubmissionTimeSeconds")
                score_detail.append({
                    "problem": p.get("index"),
                    "problem_id": f"{p.get('contestId')}-{p.get('index')}",
                    "accepted": (pr.get("points") or 0) > 0,
                    "score": pr.get("points"),
                    # 官方字段名为 rejectedAttemptCount（非 rejectedAttempts）
                    "failed_count": pr.get("rejectedAttemptCount"),
                    "reach_time_ms": best_sec * 1000 if best_sec else None,
                    "first_blood": None,
                    "post_contest_score": None,
                })

            penalty = r.get("penalty")
            if contest_type == "ICPC" and penalty is not None:
                penalty_ms = int(penalty) * 60 * 1000  # 分钟 → 毫秒，与牛客单位对齐
            else:
                penalty_ms = None

            ranks.append({
                "rank": r.get("rank"),
                "uid": handle,
                "user_name": handle,
                # organization 仅作参考，学校归属一律由「注册时填写的平台ID」绑定
                "school": party.get("organization"),
                "team": party.get("teamName"),        # 仅团队赛有值
                "accepted_count": sum(1 for pr in prs if (pr.get("points") or 0) > 0),
                "total_score": r.get("points"),
                "full_score": full_score,
                "penalty_time_ms": penalty_ms,
                "color_level": None,
                "post_contest_append": is_post,
                "is_cheater": False,   # CF 无榜单级作弊标记，字段仅为契约一致
                "score_detail": score_detail,
                "extra": {
                    "contest_type": contest_type,
                    "participant_type": ptype,
                    "successful_hacks": r.get("successfulHackCount"),
                    "unsuccessful_hacks": r.get("unsuccessfulHackCount"),
                    "room": party.get("room"),
                    "ghost": party.get("ghost"),
                },
            })
        return ranks

    # ---------- 批量抓取 ----------
    def scrape_contest_detail(self, contest_id, max_rank_pages=50,
                              filter_post_contest=False, mode="rating"):
        """
        抓取单场比赛的题目与排名。

        mode="rating"（默认，推荐）
            题目来自全站题库索引，名单来自 ratingChanges。
            名单完整、流量小（约 2MB），但没有每题明细。
        mode="standings"
            下载整场公开榜单，含每题明细，但大场次会丢 30%~40% 的人，
            仅在小场次或确需完整明细时使用。
        """
        try:
            if mode == "standings":
                problems = self.parse_problems(self.fetch_problem_list(contest_id))
                rank_info = self.fetch_all_ranks(contest_id, max_pages=max_rank_pages)
                ranks = self.parse_ranks(rank_info,
                                         filter_post_contest=filter_post_contest)
                source = "standings"
            else:
                problems = self.parse_problems(
                    self.fetch_problemset_index().get(contest_id, []))
                ok, rc, comment = self.fetch_rating_changes(contest_id)
                if not ok:
                    raise RuntimeError(f"ratingChanges 不可用: {comment}")
                ranks = self.parse_rating_changes(rc)
                source = "ratingChanges"
        finally:
            # 整场榜单占用可达数十 MB，抓完立刻释放
            self.clear_cache(contest_id)
        valid_count = sum(1 for r in ranks if not r.get("post_contest_append"))
        return {
            "problems": problems,
            "ranks": ranks,
            "rank_count": len(ranks),
            "valid_rank_count": valid_count,
            "rank_source": source,
            "crawled_at": datetime.now().isoformat(),
        }

    def enrich_ranks_with_details(self, contest_id, ranks, handles):
        """
        为指定的一批 handle 补齐每题明细（mode="rating" 下 score_detail 为空）。
        实际运行时只需传入本系统已注册的学生 handle，成本可控。
        """
        wanted = {h.lower() for h in handles or []}
        hit = 0
        for r in ranks:
            uid = (r.get("uid") or "").lower()
            if uid not in wanted:
                continue
            subs = self.fetch_user_contest_status(contest_id, r["uid"])
            if subs is None:
                continue
            detail = self.parse_user_submissions(subs)
            r["score_detail"] = detail
            r["accepted_count"] = sum(1 for d in detail if d["accepted"])
            r["extra"]["detail_source"] = "contest.status"
            hit += 1
        print(f"[enrich] 比赛 {contest_id} 补齐 {hit}/{len(wanted)} 位目标用户明细")
        return ranks

    def filter_contests(self, contests, rated_only=True, exclude_paid=True):
        """按 rated / 付费规则筛选比赛，并把判定结果写回比赛字段"""
        kept = []
        for c in contests:
            flags = self.check_rated(c)
            c.update(flags)
            if rated_only and not c.get("is_rated"):
                print(f"[filter] 排除非 rated: {c['name']} ({c.get('rated_comment')})")
                continue
            if exclude_paid and c.get("is_paid"):
                print(f"[filter] 排除付费赛: {c['name']}")
                continue
            kept.append(c)
        print(f"[filter] rated 且免费的比赛 {len(kept)}/{len(contests)} 场")
        return kept

    def run(self, months=None, output_dir=None, max_rank_pages=50,
            skip_future=True, filter_post_contest=True,
            rated_only=True, exclude_paid=True, mode="rating", handles=None):
        """
        入口：抓取比赛列表，并抓取每场比赛的排名。
        rated_only=True  只收录 rated 比赛（默认）
        exclude_paid=True 排除付费比赛（CF 无付费赛，占位保持三平台一致）
        mode="rating"    用 ratingChanges 取完整名单（推荐）
        handles          需要补齐每题明细的用户列表（本系统注册的学生）
        """
        if months is None:
            months = [datetime.now().strftime("%Y-%m")]

        out = Path(output_dir) if output_dir else Path(__file__).resolve().parent / "data" / "cf"
        out.mkdir(parents=True, exist_ok=True)

        # 1. 比赛列表（客户端按月份过滤）
        all_contests = self.parse_contests(self.fetch_contests())
        if months:
            all_contests = [
                c for c in all_contests
                if c.get("start_time") and c["start_time"][:7] in months
            ]

        # 2. 先剔除未开始的比赛，再做 rated / 付费过滤，避免无谓的 API 调用
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
                    mode=mode,
                )
                if handles:
                    detail["ranks"] = self.enrich_ranks_with_details(
                        rid, detail["ranks"], handles)
                detail["contest_meta"] = c
                # 如果题目列表为空，说明比赛尚未就绪，不保存空详情
                if not detail.get("problems"):
                    print(f"[run] 比赛 {rid} 暂无题目/排名数据，跳过保存")
                    continue
                details[rid] = detail
                detail_path = out / f"contest_{rid}.json"
                with open(detail_path, "w", encoding="utf-8") as f:
                    json.dump(detail, f, ensure_ascii=False, indent=2)
                print(f"[run] 比赛 {rid} 有效排名: {detail['valid_rank_count']} 条"
                      f"（来源 {detail['rank_source']}）")
            except Exception as e:
                print(f"[run] 抓取比赛 {rid} 失败: {e}")

        summary_path = out / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump({
                "months": months,
                "rated_only": rated_only,
                "exclude_paid": exclude_paid,
                "rank_mode": mode,
                "contest_count": len(all_contests),
                "detail_count": len(details),
                "contests": all_contests,
            }, f, ensure_ascii=False, indent=2)
        print(f"\n[run] 完成，共抓取 {len(details)}/{len(all_contests)} 场比赛详情 -> {out}")
        return details


if __name__ == "__main__":
    scraper = CodeforcesScraper()
    # 默认输出到脚本同级 data/cf/，抓取当月 rated 比赛
    # 需要多月份时传入 months=["2026-07", "2026-08", "2026-09"]
    scraper.run()
