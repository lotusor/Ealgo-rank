# E-algo rank｜爬虫层阶段总结（rated-only + 排除付费 + 学校归属改造）

> 状态：**已完成并冻结**。回归测试 66/66 通过，rated/paid 专项测试三平台全通过。

## 一、本阶段做了什么

按你定的两条硬规则改造三个爬虫：

1. **只抓 rated 比赛，付费比赛不计入**
2. **不从比赛数据里采集学校**，学校按用户注册时提供的三平台 ID 绑定

## 二、rated / paid 判定规则（已实测）

| 平台 | rated 判定依据 | paid 判定依据 |
|---|---|---|
| **Codeforces** | `contest.ratingChanges?contestId=X` 返回 `OK` 且列表非空 → rated。`phase != FINISHED` 时返回 `is_rated=None`（未定，不能判 False） | 恒 `False`，CF 无付费赛 |
| **AtCoder** | kenkoooo `contests.json` 的 `rate_change` 字段，值为 `"-"` 或空 → unrated | 恒 `False` |
| **牛客** | 逐场取 `contest-info?id=X`，要求 `category ∈ RATED_CATEGORIES` **且** `uid ∈ OFFICIAL_UIDS` | 该接口的 `needCharge` 字段 |

**AtCoder 实测分布**：6276 场中 rated 799 场 / unrated 5477 场。

**牛客 rated 系列映射**（逆向 62 场 rating-history 得出）：

| category | 官方 uid | 系列 |
|---|---|---|
| 19 | 919247 | 牛客周赛 |
| 9 | 999991351 | 小白月赛 |
| 6 | 999991351 | 练习赛 |
| 2 | 999991351 | 挑战赛 |
| 20 | 999991351 | 暑期多校训练营 |
| 21 | 999991351 | 寒假算法基础集训营 |

- `category 8`（各校自有 uid）= 校赛，**不 rated**。
- `needCharge` **逐年变化**（2021 多校 `false` / 2026 多校 `true` / 2022 寒假营 `true`），必须逐场读取，不能按系列推断。

## 三、重大发现：CF 匿名 standings 会静默丢人

匿名调用 `contest.standings` 拿到的参赛者，比 `ratingChanges` **少 28~40%**，且是其严格子集：

| 比赛 | standings | ratingChanges | 缺失率 |
|---|---|---|---|
| 2248 (Div.2) | 9190 | 13317 | 31% |
| 2244 (Div.3) | 12173 | 20340 | 40% |
| 2231 | 10818 | 15009 | 28% |
| 2200 | 9870 | 14992 | 34% |
| 2150（小场） | 961 | 961 | 0% |

**解法**：`scrape_contest_detail()` 新增 `mode` 参数

- `mode="rating"`（默认）：题目取自 `problemset.problems` 全局索引，名次取自 `ratingChanges`（完整名单，约 2MB，替代原来每场 7–9MB 的 standings 下载）。
- 需要逐题明细时，用 `enrich_ranks_with_details()` 只对**已注册学生的 handle** 调 `contest.status?contestId=X&handle=Y` 补齐 —— 该接口不受截断影响（已验证能取到 standings 里缺失用户的 AC 记录）。
- `mode="standings"`：保留全量下载模式，仅测试/特殊场景使用。

## 四、学校归属改造

三个爬虫的 rank 输出 `school` **一律为 `None`**，平台自带的学校字段全部降级到 `extra`，仅供人工核对：

| 平台 | 原字段 | 现位置 |
|---|---|---|
| CF | `party.organization` | `extra.organization` |
| AtCoder | `Affiliation` | `extra.affiliation`（12876 人中 3601 人填写） |
| 牛客 | `school` | `extra.profile_school` |

学校归属完全交给业务侧：用户注册时填 CF handle / AtCoder user_id / 牛客 uid，补全学校信息后自动绑定这些 ID。

## 五、改动的文件

| 文件 | 说明 |
|---|---|
| `crawlers/cf_scraper.py` | 大改。新增 `fetch_rating_changes` / `check_rated` / `parse_rating_changes` / `fetch_user_contest_status` / `parse_user_submissions` / `fetch_problemset_index` / `enrich_ranks_with_details` / `filter_contests`；`run()` 新增 `rated_only`、`exclude_paid`、`mode`、`handles` 参数 |
| `crawlers/atcoder_scraper.py` | 新增 `check_rated` / `filter_contests`；`school` 置 None，Affiliation 移入 extra |
| `crawlers/nowcoder_scraper.py` | 新增 `fetch_contest_info` / `check_rated` / `filter_contests` 与 rated 映射常量；`school` 置 None |
| `crawlers/verify_rated.py` | **新建**。rated/paid 专项回归测试（`cf` \| `at` \| `nc` \| `all`），三平台全通过 |
| `crawlers/verify_scrapers.py` | 同步契约变更：CF 明细断言改走 `mode="standings"`，AtCoder `expect_school=False` 并新增 Affiliation 降级断言 |
| `crawlers/VERIFICATION.md` | 新增「二·五 rated-only 与排除付费」「二·六 学校归属改为平台 ID 绑定」两节 |

临时探测脚本 `_probe_*.py`（7 个）与 `__pycache__` 已清理，目录只剩 6 个正式文件。

## 六、验证结果

- `verify_scrapers.py all` → **66/66 通过，0 失败**
- `verify_rated.py all` → CF / AtCoder / 牛客 全部通过
  - CF 2216 Unrated → `is_rated=False`；2248 Div.2 → `True`；`is_paid` 恒 `False`
  - 牛客 133876（多校）→ rated + paid；23106（寒假营）→ rated + paid；137532 / 137658 → unrated
  - 过滤器只保留 `{138240, 137264, 137418, 82612}`

## 七、后续注意事项

- 牛客存在作弊标记账号（`userName` 前缀「【已被标记为作弊】」），入库前需过滤。
- 牛客 rated 判定要逐场请求 `contest-info`，比赛多时需加缓存与限速（已有 `_info_cache`）。
- 牛客抓取最慢（1100 人约 65s），Celery 接入时建议单独队列并设超时。
- 清理文件时相对路径 `rm` 会被安全删除机制拦截，**必须用绝对路径**。

## 八、下一步

爬虫层已冻结，进入 **Phase 1：Django 骨架**（任务 #1~#9 尚未开始）。
