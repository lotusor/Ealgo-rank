"""洛谷比赛排期 provider —— 只读官方赛事列表，产出日历排期行。

为什么单独一个源、不走 clist：clist 覆盖 20+ 平台但没有计分字段，洛谷场次在 clist
里只能靠比赛名后缀的 `[rated, ioi]` 标签猜；而洛谷自己的赛事列表就带着官方判定
整数 `rated`。2026-09-26 实测把位含义钉死：

    rated & 1  计入「咕值」（参与度分，不动等级分）
    rated & 2  计入「等级分」—— 这才是站内 `is_rated`（"计入平台 rating"）的口径

真值对照（取自页面自己渲染的官方文案）：
    rated=1     ICPC 区域赛重现赛  「本场比赛**不**计算等级分，但**计入咕值比赛分**」
    rated=3     LGR 月赛 / 各类公开赛  「本场计入咕值计算」+「本场计入等级分」
    rated=65539 LGR 基础赛          同上（高位是结算/公布标记，不影响低两位）
⚠️ 页面上那枚 "Rated" 彩色标签连 rated=1 的重现赛都挂着，**不能**用名字或标签里的
"Rated" 字样当判定 —— 只有位运算准。这也是洛谷比 CF 强的地方：CF 预告期只能预判。

反爬与取数口径：整站在 CDN 后面，无 cookie 时返回 302 自跳并下发 `Set-Cookie: C3VK`；
`requests.Session` 跟随重定向即完成握手（实测不必执行 JS）。响应是服务端渲染的
HTML，正文内嵌 `<script id="lentille-context" type="application/json">`，本模块只
解析这段 JSON、不碰 HTML 结构。老接口 `?_content_=json:...` 已废弃（同样返回 HTML），
URL 上的 `status` / `type` / `keyword` 等筛选参数服务端一律忽略 —— 过滤只能在本地做。
列表按 `startTime` 降序（最远的未来场在最前），所以翻到「已经越过窗口下界」就停。

本期只做日历：榜单页 `/contest/<id>/rankings` 实测 404、用户页 `/user/<uid>` 实测
403（需登录），拿不到逐人名次，因此不爬成绩、不计分、不开放绑定 —— 平台的这些
能力一律在 `apps/common/platforms.py` 的注册表里声明，由启动自检把关。
"""

import json
import logging
import random
import re
import time

import requests

logger = logging.getLogger(__name__)

BASE = "https://www.luogu.com.cn"
LIST_URL = f"{BASE}/contest/list"

# 官方 JSON 嵌在这段 script 里，type="application/json" 保证它可直接 json.loads。
# 属性顺序不写进模式：只锚定 id，哪天模板改成 type 在前也不必回来修正则。
CONTEXT_TAG = re.compile(
    r'<script id="lentille-context"[^>]*>(.*?)</script>', re.S)

RATED_GUZHI = 1        # rated 位：计入咕值
RATED_ELO = 2          # rated 位：计入等级分 —— 站内 is_rated 只认这一位

#: 赛制整数 → 展示名（1=OI、2=ICPC、4=IOI 为实测，3 按页面筛选项「乐多」推得）
METHOD_LABELS = {1: "OI", 2: "ICPC", 3: "乐多", 4: "IOI"}


def is_rated_by_flag(flag):
    """官方 `rated` 整数 → 是否计入等级分。缺字段/解不开返回 None（判不出）。"""
    if flag is None or flag == "":
        return None
    try:
        return bool(int(flag) & RATED_ELO)
    except (TypeError, ValueError):
        return None


def series_of(name, host=None):
    """洛谷赛事系列。这条口径将来 `crawl_luogu` 转正时必须逐字复用，否则同一场
    比赛会在「系列」下拉里出现两个串（与 clist `_series_of` 同一条约束）。

    ⚠️ 不要加「月月赛」这种关键字：官方命名是「洛谷 9 月月赛」，「9 月」+「月赛」
    天然拼出「月月赛」，先匹配它就会把月赛错分成一个独立系列（实测踩过）。
    """
    n = (name or "").strip()
    for kw, label in (("月赛", "洛谷月赛"), ("基础赛", "洛谷基础赛"),
                      ("入门赛", "洛谷入门赛"), ("新春", "洛谷新春赛"),
                      ("模拟", "洛谷模拟赛")):
        if kw in n:
            return label
    if (host or {}).get("id") == 1000:      # 1000 = 洛谷官方团队
        return "洛谷官方赛"
    return "洛谷公开赛"


class LuoguScraper:
    """洛谷赛事列表客户端。只读列表，不碰榜单、不写落盘缓存。"""

    #: 一次同步最多翻几页。列表降序，正常一轮 1~2 页就越过窗口下界；触顶说明
    #: 上游排期异常密集或翻页失效，必须报出来而不是静默给出半张日历。
    MAX_PAGES = 6
    #: 官方每页 20 条。拿不满一页就是真到底了（meta 里的 total 不可当页数用）。
    PER_PAGE = 20
    DAY = 86400

    def __init__(self, timeout=30, delay=(1.5, 3.0)):
        self.timeout = timeout
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/"
                           "537.36 (KHTML, like Gecko) Chrome/124.0.0.0 "
                           "Safari/537.36"),
            "Accept": ("text/html,application/xhtml+xml,"
                       "application/json;q=0.9,*/*;q=0.8"),
            "Accept-Language": "zh-CN,zh;q=0.9",
        })

    def fetch_upcoming(self, days_ahead=90, **kwargs):
        """返回 [标准化排期行]：进行中 + 未来 days_ahead 天内开赛，且官方计等级分。

        「只收 rated」是产品口径（2026-09-26 确认）：非计分的咕值场/自测场不进
        日历。判不出 rated 的行同样丢掉 —— 宁可少一场，也不要一行永远亮不起来。
        时间给秒级时间戳，与 clist 行同口径，由入库层 `_parse_dt` 统一转成 aware。
        """
        now = int(time.time())
        floor = now - self.DAY          # 昨天起：进行中的场次也要看得见
        ceil = now + days_ahead * self.DAY
        kept, dropped, oldest = [], 0, now
        for page in range(1, self.MAX_PAGES + 1):
            contests = self._fetch_page(page)
            if not contests:
                break
            starts = []
            for c in contests:
                start, end = c.get("startTime"), c.get("endTime")
                if not isinstance(start, int) or not isinstance(end, int):
                    dropped += 1
                    continue
                starts.append(start)
                if end < floor or start > ceil:
                    continue
                row = self._to_row(c, start, end)
                if row is None:
                    dropped += 1
                    continue
                kept.append(row)
            oldest = min(starts + [oldest])
            if len(contests) < self.PER_PAGE or oldest < floor:
                break
            self._sleep()
        else:
            logger.warning("洛谷排期翻页达到上限 %s 页，窗口 %s 天可能未取全",
                           self.MAX_PAGES, days_ahead)
        logger.info("洛谷排期取数完成：计分场次 %s 场（按 rated 口径与窗口丢弃 %s 行）",
                    len(kept), dropped)
        return kept

    # ---------------------------------------------------------------- 取数

    def _fetch_page(self, page):
        """一页 → 官方 contests 数组。任何异常都抛出，由同步任务保留上一轮数据。"""
        resp = self.session.get(LIST_URL, params={"page": page},
                                timeout=self.timeout)
        resp.raise_for_status()
        m = CONTEXT_TAG.search(resp.text)
        if not m:
            raise RuntimeError(
                f"洛谷第 {page} 页响应里没有 lentille-context JSON"
                f"（多半是 CDN 挑战换了形态，需要重新摸握手）")
        payload = json.loads(m.group(1))
        if payload.get("status") != 200:
            raise RuntimeError(f"洛谷第 {page} 页返回状态 {payload.get('status')}")
        contests = (payload.get("data") or {}).get("contests") or {}
        rows = contests.get("result")
        if rows is None:
            raise RuntimeError(f"洛谷第 {page} 页响应里没有 contests.result")
        return rows

    def _sleep(self):
        time.sleep(random.uniform(*self.delay))

    # ---------------------------------------------------------------- 归一

    def _to_row(self, c, start, end):
        """官方一条场次 → 站内标准化排期行（字段与 clist 行对齐）。"""
        eid = c.get("id")
        rated = is_rated_by_flag(c.get("rated"))
        if eid is None or not rated:
            return None
        method = METHOD_LABELS.get(c.get("method"), "")
        return {
            "platform": "luogu",
            "contest_id": str(eid), "real_contest_id": str(eid),
            "name": str(c.get("name") or f"洛谷比赛 {eid}")[:255],
            "link": f"{BASE}/contest/{eid}",
            "start_time": int(start), "end_time": int(end),
            "duration_minutes": int((end - start) // 60),
            "series": series_of(c.get("name"), c.get("host")),
            "source": "luogu",
            "is_rated": True,
            "is_paid": False,
            "rated_comment": (f"官方 rated={int(c.get('rated') or 0)}：计入等级分"
                              + (f"（{method} 赛制）" if method else ""))[:255],
        }
