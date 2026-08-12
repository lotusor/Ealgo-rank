#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
牛客网比赛信息与用户排名爬虫
- 从移动端首页建立会话，绕过 PC 端滑块验证
- 抓取比赛日历、比赛题目、实时排名（含每题提交详情）
- 支持多月份、多场比赛批量抓取

【只收录 rated 且免费的比赛】
  牛客日历接口不含 rated / 收费字段，需逐场请求
  acm-heavy/acm/contest/contest-info?id=X，用两个字段判定：

    是否 rated：uid（主办方）+ category（赛事系列）
      category=19 uid=919247    牛客周赛
      category=9  uid=999991351 牛客小白月赛
      category=6  uid=999991351 牛客练习赛
      category=2  uid=999991351 牛客挑战赛
      category=20 uid=999991351 牛客暑期多校训练营
      category=21 uid=999991351 牛客寒假算法基础集训营
      category=8  各校 uid       校赛/自主命题赛 -> 不计 rating
    是否收费：needCharge（布尔）
      注意同一系列不同年份收费状态会变：2021 多校 needCharge=false，
      2026 多校 needCharge=true，2022 寒假营 needCharge=true。
      所以必须逐场读取，不能按系列推断。

  上述规则由用户 rating-history 反查 62 场 rated 比赛后归纳得到。
"""

import json
import random
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests


class NowCoderScraper:
    """牛客比赛信息爬虫"""

    def __init__(self, delay=(1.5, 3.5), timeout=20):
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
                "Mobile/15E148 Safari/604.1"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "Referer": "https://m.nowcoder.com/",
            "Connection": "keep-alive",
        })
        self.base = "https://ac.nowcoder.com"
        self.rank_page_size = 50  # 实测每页固定 50 条
        self._info_cache = {}

    # 计入 rating 的官方赛事：category -> 系列名
    RATED_CATEGORIES = {
        19: "牛客周赛",
        9: "牛客小白月赛",
        6: "牛客练习赛",
        2: "牛客挑战赛",
        20: "牛客暑期多校训练营",
        21: "牛客寒假算法基础集训营",
    }
    # 官方主办账号，用于排除第三方仿冒同名比赛
    OFFICIAL_UIDS = {919247, 999991351}

    # 牛客对判定作弊的账号会在榜单 userName 前拼接标记文案。
    # 这类记录必须排除出积分统计，否则会污染学校排名。
    # 中英文方括号、标记文案的历史变体都要覆盖，宁可多匹配也不能漏。
    CHEATER_PATTERN = re.compile(
        r"^\s*[\[\【\(\（]\s*(?:该用户)?已?被?(?:平台)?标记为作弊[^\]\】\)\）]*[\]\】\)\）]\s*"
    )

    # ---------- 底层请求 ----------
    def _sleep(self):
        time.sleep(random.uniform(*self.delay))

    def _get(self, url, **kwargs):
        self._sleep()
        resp = self.session.get(url, timeout=self.timeout, **kwargs)
        resp.raise_for_status()
        return resp

    def init_session(self):
        """访问移动端首页，建立会话并获取基础 Cookie"""
        resp = self._get("https://m.nowcoder.com/")
        print(f"[init_session] 首页 OK, cookies={self.session.cookies.get_dict()}")
        return resp

    # ---------- 比赛列表 ----------
    def fetch_contests(self, year_month=None):
        """抓取指定月份的比赛日历"""
        if year_month is None:
            year_month = datetime.now().strftime("%Y-%m")
        ts = int(time.time() * 1000)
        url = f"{self.base}/acm/calendar/contest?token=&month={year_month}&_={ts}"
        resp = self._get(url)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"比赛日历接口返回错误: {data}")
        contests = data.get("data", [])
        print(f"[fetch_contests] {year_month} 共 {len(contests)} 条比赛记录")
        return contests

    def parse_contests(self, contests, only_nowcoder=True):
        """解析比赛列表，提取标准化字段"""
        results = []
        for c in contests:
            if only_nowcoder and c.get("ojName") != "NowCoder":
                continue
            link = c.get("link", "")
            real_id = self._extract_real_contest_id(link)
            results.append({
                "contest_id": c.get("contestId"),
                "real_contest_id": real_id,
                "name": c.get("contestName"),
                "oj": c.get("ojName"),
                "link": link,
                "start_time": self._ts2str(c.get("startTime")),
                "end_time": self._ts2str(c.get("endTime")),
                "duration_minutes": (c.get("endTime", 0) - c.get("startTime", 0)) // 60000,
            })
        return results

    @staticmethod
    def _extract_real_contest_id(link):
        """比赛日历返回的 contestId 与详情页 URL 中的 id 不同，需从 link 解析"""
        m = re.search(r"/acm/contest/(\d+)", link)
        return int(m.group(1)) if m else None

    @staticmethod
    def _ts2str(ts_ms):
        if not ts_ms:
            return None
        return datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")

    # ---------- rated / 收费判定 ----------
    def fetch_contest_info(self, real_contest_id, use_cache=True):
        """抓取比赛详情（含 category / uid / needCharge），失败返回 None"""
        if use_cache and real_contest_id in self._info_cache:
            return self._info_cache[real_contest_id]
        ts = int(time.time() * 1000)
        url = (f"{self.base}/acm-heavy/acm/contest/contest-info"
               f"?id={real_contest_id}&_={ts}")
        try:
            data = self._get(url).json()
        except Exception as e:
            print(f"[fetch_contest_info] {real_contest_id} 失败: {e}")
            return None
        if data.get("code") != 0:
            print(f"[fetch_contest_info] {real_contest_id} 返回错误: {data.get('msg')}")
            return None
        info = data.get("data") or {}
        if use_cache:
            self._info_cache[real_contest_id] = info
        return info

    def check_rated(self, contest_meta):
        """
        统一契约方法：判定一场比赛是否 rated / 是否付费。
        需要额外一次 contest-info 请求。
        """
        rid = contest_meta.get("real_contest_id") or contest_meta.get("contest_id")
        info = self.fetch_contest_info(rid)
        if info is None:
            return {"is_rated": None, "is_paid": None,
                    "rated_source": "contest-info",
                    "rated_comment": "详情接口不可用，无法判定"}
        category = info.get("category")
        uid = info.get("uid")
        need_charge = bool(info.get("needCharge"))
        series = self.RATED_CATEGORIES.get(category)
        is_rated = bool(series) and uid in self.OFFICIAL_UIDS
        return {
            "is_rated": is_rated,
            "is_paid": need_charge,
            "rated_source": "contest-info:category+uid+needCharge",
            "rated_comment": (f"category={category}({series or '非官方rated系列'}) "
                              f"uid={uid} needCharge={need_charge}"),
            "series": series,
            "category": category,
            "organizer_uid": uid,
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
                print(f"[filter] 排除付费赛: {c['name']} ({c.get('rated_comment')})")
                continue
            kept.append(c)
        print(f"[filter] rated 且免费的比赛 {len(kept)}/{len(contests)} 场")
        return kept

    # ---------- 题目列表 ----------
    def fetch_problem_list(self, real_contest_id):
        """抓取某场比赛的题目列表"""
        ts = int(time.time() * 1000)
        url = f"{self.base}/acm/contest/problem-list?token=&id={real_contest_id}&_={ts}"
        resp = self._get(url)
        data = resp.json()
        if data.get("code") != 0:
            print(f"[fetch_problem_list] {real_contest_id} 获取失败: {data.get('msg')}")
            return []
        problems = data.get("data", {}).get("data", [])
        print(f"[fetch_problem_list] {real_contest_id} 共 {len(problems)} 题")
        return problems

    @staticmethod
    def parse_problems(problems):
        return [{
            "index": p.get("index"),
            "title": p.get("title"),
            "problem_id": p.get("problemId"),
            "score": p.get("score"),
            "total_score": p.get("totalScore"),
            "submit_count": p.get("submitCount"),
            "accepted_count": p.get("acceptedCount"),
            "submit_person_count": p.get("submitPersonCount"),
        } for p in problems]

    # ---------- 排名数据 ----------
    def fetch_rank_page(self, real_contest_id, page=1):
        """抓取单页排名（page 从 1 开始，每页 50 条）"""
        ts = int(time.time() * 1000)
        url = (
            f"{self.base}/acm-heavy/acm/contest/real-time-rank-data"
            f"?token=&id={real_contest_id}&limit=0&page={page}&_={ts}"
        )
        resp = self._get(url)
        data = resp.json()
        if data.get("code") != 0:
            print(f"[fetch_rank_page] {real_contest_id} page={page} 失败: {data.get('msg')}")
            return None
        return data.get("data", {})

    def fetch_all_ranks(self, real_contest_id, max_pages=None):
        """
        分页抓取排名，直到读完总页数、返回空页或触及安全上限。
        牛客每页固定 50 条，赛后补交记录 ranking=0，会排在正常排名之后。
        首页 basicInfo.pageCount 是权威总页数，据此精确翻页；
        max_pages=None 表示抓完整场（大型比赛可达数百页），传数值则作为安全上限。
        """
        all_ranks = []
        problem_data = []
        basic_info = {}
        total_pages = None
        page = 1
        while True:
            chunk = self.fetch_rank_page(real_contest_id, page)
            if chunk is None:
                break
            ranks = chunk.get("rankData", [])
            if not ranks:
                break
            if page == 1:
                problem_data = chunk.get("problemData", [])
                basic_info = chunk.get("basicInfo") or {}
                total_pages = basic_info.get("pageCount")
                if max_pages and total_pages and total_pages > max_pages:
                    print(f"[fetch_all_ranks] {real_contest_id} 共 {total_pages} 页 "
                          f"({basic_info.get('rankCount')} 人)，受 max_pages={max_pages} 限制将被截断")
            all_ranks.extend(ranks)
            print(f"[fetch_all_ranks] {real_contest_id} page={page}/{total_pages or '?'} "
                  f"获取 {len(ranks)} 条，累计 {len(all_ranks)}")
            # 当前页不足 50 条说明已到末尾
            if len(ranks) < self.rank_page_size:
                break
            limits = [x for x in (total_pages, max_pages) if x]
            if limits and page >= min(limits):
                break
            page += 1
        return {
            "basic_info": basic_info,
            "problem_data": problem_data,
            "rank_data": all_ranks,
        }

    @classmethod
    def detect_cheater(cls, user_name):
        """
        识别牛客平台标记的作弊账号。
        返回 (is_cheater, clean_name, raw_name)。
        clean_name 已剥离标记前缀，便于展示与匹配；raw_name 保留原文供审计。
        """
        raw = user_name or ""
        m = cls.CHEATER_PATTERN.match(raw)
        if m:
            return True, raw[m.end():].strip(), raw
        return False, raw.strip(), raw

    @classmethod
    def parse_ranks(cls, rank_info, filter_post_contest=False, exclude_cheaters=False):
        """
        解析并简化排名数据。
        filter_post_contest=True 时过滤掉赛后补交记录（postContestAppend 或 ranking<=0）。
        exclude_cheaters=True 时直接丢弃平台标记的作弊账号；
          默认 False —— 爬虫层只打 is_cheater 标记、保留原始数据可追溯，
          由入库层决定是否计入积分（避免静默丢数据导致对不上账）。

        注意：榜单里的 school 是用户在牛客个人资料里自填的，缺失率高且写法混乱，
        不作为学校归属依据，仅放进 extra 供人工核对。
        学校归属一律由注册时绑定的牛客 uid 决定。
        """
        # problemId -> 题号（A/B/C...），反向索引避免逐条线性查找
        pid2name = {
            p.get("problemId"): p.get("name")
            for p in rank_info.get("problem_data", [])
        }
        # ICPC 赛制的 scoreList 无 reachTime，只有绝对时间戳 acceptedTime，
        # 用开赛时间换算成相对赛程的毫秒数，与 OI 赛制的 reachTime 语义对齐
        begin_time = (rank_info.get("basic_info") or {}).get("contestBeginTime")

        ranks = []
        cheater_count = 0
        for r in rank_info.get("rank_data", []):
            is_post = bool(r.get("postContestAppend")) or (r.get("ranking", 0) <= 0)
            if filter_post_contest and is_post:
                continue

            is_cheater, clean_name, raw_name = cls.detect_cheater(r.get("userName"))
            if is_cheater:
                cheater_count += 1
                if exclude_cheaters:
                    continue

            score_detail = []
            for s in r.get("scoreList", []):
                reach = s.get("reachTime")
                if reach is None:
                    acc_time = s.get("acceptedTime")
                    if acc_time and begin_time:
                        reach = acc_time - begin_time
                score_detail.append({
                    "problem": pid2name.get(s.get("problemId")),
                    "problem_id": s.get("problemId"),
                    "accepted": s.get("accepted"),
                    "score": s.get("score"),
                    "failed_count": s.get("failedCount"),
                    "reach_time_ms": reach,
                    "first_blood": s.get("firstBlood"),
                    "post_contest_score": s.get("postContestScore"),
                })
            ranks.append({
                "rank": r.get("ranking"),
                "uid": r.get("uid"),
                "user_name": clean_name,
                "school": None,   # 不从比赛数据推断学校，见上方说明
                "team": r.get("team"),
                "accepted_count": r.get("acceptedCount"),
                "total_score": r.get("totalScore"),
                "full_score": r.get("fullScore"),
                "penalty_time_ms": r.get("penaltyTime"),
                "color_level": r.get("colorLevel"),
                "post_contest_append": is_post,
                "is_cheater": is_cheater,   # 平台标记作弊，入库时不计积分
                "score_detail": score_detail,
                "extra": {
                    "rank_type": (rank_info.get("basic_info") or {}).get("rankType"),
                    "team_member_uids": r.get("teamMemberUids"),
                    "profile_school": r.get("school"),  # 用户自填，仅供参考
                    "raw_user_name": raw_name if is_cheater else None,
                },
            })
        if cheater_count:
            action = "已剔除" if exclude_cheaters else "已标记"
            print(f"[parse_ranks] 检出作弊账号 {cheater_count} 个（{action}）")
        return ranks

    # ---------- 批量抓取 ----------
    def scrape_contest_detail(self, real_contest_id, max_rank_pages=None,
                              filter_post_contest=False, exclude_cheaters=False):
        """抓取单场比赛的题目与全部有效排名"""
        problems = self.parse_problems(self.fetch_problem_list(real_contest_id))
        rank_info = self.fetch_all_ranks(real_contest_id, max_pages=max_rank_pages)
        ranks = self.parse_ranks(rank_info, filter_post_contest=filter_post_contest,
                                 exclude_cheaters=exclude_cheaters)
        cheater_count = sum(1 for r in ranks if r.get("is_cheater"))
        # 可计入积分的记录：非赛后补交 且 非作弊
        valid_count = sum(1 for r in ranks
                          if not r.get("post_contest_append") and not r.get("is_cheater"))
        return {
            "problems": problems,
            "ranks": ranks,
            "rank_count": len(ranks),
            "valid_rank_count": valid_count,
            "cheater_count": cheater_count,
            "crawled_at": datetime.now().isoformat(),
        }

    def run(self, months=None, output_dir=None, max_rank_pages=None,
            skip_future=True, filter_post_contest=True,
            rated_only=True, exclude_paid=True, exclude_cheaters=False):
        """
        入口：抓取多月份比赛列表，并抓取每场比赛的全部有效排名。
        rated_only=True      只收录官方 rated 系列（周赛/小白月赛/练习赛/挑战赛/多校/寒假营）
        exclude_paid=True    排除 needCharge=true 的付费比赛
        exclude_cheaters=False 默认保留作弊账号但打 is_cheater 标记，入库层负责排除
        """
        if months is None:
            months = [datetime.now().strftime("%Y-%m")]

        out = (Path(output_dir) if output_dir
               else Path(__file__).resolve().parent / "data" / "nowcoder")
        out.mkdir(parents=True, exist_ok=True)

        self.init_session()

        # 1. 比赛列表
        all_contests = []
        for ym in months:
            raw = self.fetch_contests(ym)
            all_contests.extend(self.parse_contests(raw, only_nowcoder=True))

        # 2. 剔除未开始的比赛，再做 rated / 付费过滤
        #    先剔未开始的可以少发很多次 contest-info 请求
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
                    exclude_cheaters=exclude_cheaters,
                )
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
                      f"（作弊 {detail.get('cheater_count', 0)} 条已排除）")
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

    @staticmethod
    def _str2ts(s):
        if not s:
            return None
        try:
            return int(datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
        except Exception:
            return None


if __name__ == "__main__":
    scraper = NowCoderScraper()
    # 默认输出到脚本同级 data/nowcoder/，抓取当月比赛，
    # 按 basicInfo.pageCount 自动翻页直到读完所有有效排名
    # 需要多月份时传入 months=["2026-07", "2026-08", "2026-09"]
    scraper.run()
