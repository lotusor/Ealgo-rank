"""clist.by 聚合赛事 API —— 竞赛日历的排期源。

为什么换它：三个官方源里 CF 与牛客只给得出近处排期，kenkoooo 的
`contests.json` 实测（2026-09-23）最新一条就是当天、根本不含未来场；自己再去摸
atcoder.jp archive、洛谷、CodeChef… 每站一套解析。clist 一次请求覆盖 20+ 平台，
且支持 `resource__in` 服务端过滤，我们只认其中三平台时通常一个请求就够。

凭据：`CLIST_USERNAME` / `CLIST_API_KEY` 走环境变量（本地 .env、生产 .env.prod，
两者都在 .gitignore 里），绝不写进代码或提交。标称限速 10 req/min。

平台归属按 `resource`（就是 host 串）判定，`external_id` 从 `href` 里反解：
resource id 是对方库的主键会变，而 URL 里那段 id 正是站内 `Contest.external_id`
的口径（CF=contestId、AtCoder=abc469、牛客=详情页 id）。这样比赛结束后正常爬取
走 `update_or_create(platform, external_id)` 能原地转正，不留双行。

2026-09-23 实测的响应口径（写死在代码里的字段名以此为准）：
    objects[]: {id, event, href, resource, resource_id, start, end, duration, ...}
    meta:      {limit, offset, next, previous, estimated_count}
    时间是不带时区的 **UTC** 裸串；CF 的 href 用复数 `/contests/<id>`。
"""

import logging
import random
import re
import time
from datetime import date, datetime, timedelta, timezone as dt_timezone

import requests

logger = logging.getLogger(__name__)

API_URL = "https://clist.by/api/v4/contest/"

# 站内 Platform 值 -> (clist 的 resource 串, 从 href 取 external_id 的正则)。
# 扩平台时在这里加一行 + 后端 `Platform` 枚举加一项即可。
# CF 的 href 在 clist 里是复数 `/contests/<id>`、站内与官方 API 用单数，两种都认；
# 但**不认 gym**：`crawl_codeforces` 拉的是 `contest.list?gym=false`，gym 场次进了
# 日历就永远转不了正，只会变成一条点不出结果的僵尸排期。
PLATFORMS = {
    "codeforces": ("codeforces.com", re.compile(r"codeforces\.com/contests?/(\d+)")),
    "atcoder": ("atcoder.jp", re.compile(r"atcoder\.jp/contests/([a-z0-9_-]+)")),
    "nowcoder": ("ac.nowcoder.com",
                 re.compile(r"(?:ac|www)\.nowcoder\.com/acm/contest/(\d+)")),
}
RESOURCE_FILTER = ",".join(host for host, _ in PLATFORMS.values())

# clist 会在比赛名后挂计分方式标记（"牛客挑战赛92 [ACM]"），站内不要这串噪音
MODE_TAG = re.compile(r"\s*\[[A-Za-z, ]+\]\s*$")


class ClistScraper:
    """只读排期客户端。不抓榜单、不碰落盘缓存。"""

    def __init__(self, username, api_key, timeout=30, delay=(1.0, 2.0),
                 page_limit=100, max_pages=5):
        if not username or not api_key:
            raise ValueError("clist 凭据未配置（CLIST_USERNAME / CLIST_API_KEY）")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"ApiKey {username}:{api_key}",
            "User-Agent": "e-acm-rank/1.0 (contest calendar sync)",
        })
        self.timeout = timeout
        self.delay = delay
        self.page_limit = page_limit
        self.max_pages = max_pages

    def fetch_upcoming(self, days_ahead=90):
        """返回 [标准化排期行]，覆盖「进行中 + 未来 days_ahead 天内开赛」。

        窗口下界取 `end__gte=今天-1`：进行中的比赛（start 已过、end 未到）也要进
        日历，否则当天开赛的场次要等到第二天才看得见。
        """
        params = {
            "resource__in": RESOURCE_FILTER,
            "end__gte": (date.today() - timedelta(days=1)).isoformat(),
            "start__lte": (date.today() + timedelta(days=days_ahead)).isoformat(),
            "order_by": "start",
            "limit": self.page_limit,
        }
        rows = []
        objects = []
        for page in range(self.max_pages):
            payload = self._get(params)
            objects = payload.get("objects") or []
            rows.extend(r for r in (self._to_row(o) for o in objects) if r)
            # meta.next 即使没有后继也会给出，只有「本页没拿满」才是真到底了
            if len(objects) < self.page_limit:
                break
            params = {"limit": self.page_limit,
                      "offset": int(params.get("offset", 0)) + self.page_limit}
            self._sleep()
        else:
            # 翻满上限仍拿满一页 → 窗口里还有数据没取到，必须报出来，
            # 否则「日历只到某个月」会被当成上游本来就没有排期
            if len(objects) >= self.page_limit:
                logger.warning("clist 排期翻页达到上限 %s 页（每页 %s 条），窗口 %s 天的"
                               "排期可能未取全", self.max_pages, self.page_limit,
                               days_ahead)
        logger.info("clist 排期取数完成：三平台 %s 场（窗口 %s 天）",
                    len(rows), days_ahead)
        return rows

    def _get(self, params):
        resp = self.session.get(API_URL, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict) or "objects" not in data:
            raise RuntimeError(f"clist 返回结构异常: {str(data)[:120]}")
        return data

    def _sleep(self):
        time.sleep(random.uniform(*self.delay))

    @staticmethod
    def _platform_of(obj):
        """先看 resource（就是 host 串），拿不到再退到 href 正则。"""
        resource = (obj.get("resource") or "").lower()
        href = (obj.get("href") or "").lower()
        for platform, (host, pattern) in PLATFORMS.items():
            if resource == host or (not resource and pattern.search(href)):
                m = pattern.search(href)
                if m:
                    return platform, m.group(1)
        return None, None

    @classmethod
    def _to_row(cls, obj):
        """时间统一换成秒级时间戳交给入库层（`ingest._parse_dt` 认 int/float→UTC），
        避免各处再猜时区。"""
        platform, external_id = cls._platform_of(obj)
        if not platform:
            return None
        start = _utc_iso_to_epoch(obj.get("start"))
        if start is None:
            return None
        end = _utc_iso_to_epoch(obj.get("end"))
        dur = int(obj.get("duration") or 0)
        if end is None and dur:
            end = start + dur
        return {
            "platform": platform,
            "contest_id": external_id,
            "real_contest_id": external_id,
            "name": MODE_TAG.sub("", obj.get("event") or external_id).strip()[:255],
            "link": obj.get("href") or "",
            "start_time": start,
            "end_time": end,
            "duration_minutes": (int(end) - start) // 60 if end else None,
            "series": _series_of(platform, obj.get("event") or "",
                                 obj.get("href") or ""),
            "source": "clist",
        }


def _utc_iso_to_epoch(value):
    """clist 给的是无时区裸串，按 UTC 解释（2026-09-23 与 CF 官方 startTimeSeconds
    逐场比对过：同一场比赛两边换算结果一致）。"""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "").strip())
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_timezone.utc)
    return int(dt.timestamp())


def _series_of(platform, name, href):
    """系列名与三个官方爬虫的 extract_series 同口径，否则同一场比赛转正前后会在
    「系列」下拉里出现两个串。"""
    if platform == "codeforces":
        if "Educational" in name:
            return "Educational"
        if "Global" in name:
            return "Global"
        m = re.search(r"\(Div\.\s*(\d+)\)", name)
        return f"Div. {m.group(1)}" if m else ""
    if platform == "atcoder":
        m = re.search(r"/contests/([a-z]+)\d+", href.lower())
        return m.group(1).upper() if m else ""
    m = re.search(r"(牛客[\u4e00-\u9fa5]{0,10}?(?:周赛|月赛|挑战赛|集训营|练习赛|题解))",
                  name)
    return m.group(1) if m else ""
