# 三平台抓取脚本联网验证报告

验证时间：2026-08-04
验证方式：真实调用线上接口抓取样本比赛，校验统一契约字段与数据正确性
验证工具：`verify_scrapers.py`（可重复执行，用于后续回归）

## 一、结论

| 平台 | 状态 | 样本 | 数据量 | 断言 |
|---|---|---|---|---|
| Codeforces | 可用 | Div.3 (ICPC制) + Div.2 (CF制) | 21363 条排名 / 149541 条题目明细 | 26/26 |
| AtCoder | 可用（换端点后） | ABC469 | 12876 条排名 | 12/12 |
| 牛客 | 可用 | 河南萌新联赛(ICPC制) + 周赛155(OI制) | 400 条抽样 + 1100 条全量 | 27/27 |

初版脚本**并非全部可用**：AtCoder 的排名抓取完全失效，Codeforces 与牛客各有字段级缺陷。
以下问题均已修复并复验通过。

## 二、发现并修复的问题

### AtCoder（致命，整条链路失效）

1. **`/contests/{id}/standings/json` 需要登录**
   实测未登录返回 `302 → /login?continue=...`，`standings` HTML 页同样跳转。
   初版脚本依赖该端点，排名抓取 100% 拿不到数据。
   **修复**：改用官方 `/contests/{id}/results/json`，免登录直接返回 200。
   ABC469 实测 12876 条，含 `Place`（名次）、`Performance`（表现分）、
   `OldRating/NewRating`、`IsRated`、`Affiliation`、`Country`。

2. **`school` 被写死为 `None`**
   `results/json` 的 `Affiliation` 字段就是所属机构/学校。
   ABC469 实测 3601/12876 条非空（约 28%），如 `University of Warsaw`。
   **修复**：`school` 取 `Affiliation`。

3. **题目列表随 standings 一起失效**
   **修复**：改用 kenkoooo 的 `contest-problem.json` + `problems.json`
   建立全局索引（9297 题 / 6268 场），会话内只拉一次。

4. **代价**：`results` 端点不含每题提交详情，`score_detail` 恒为空列表。
   若确需每题详情，只能走 kenkoooo `/v3/from/{unix_second}` 提交流按比赛时间窗回放，
   一场 ABC 需数十次请求，成本高，暂不实现。

### Codeforces

1. **字段名写错导致 `failed_count` 恒为 `None`**
   官方字段是 `rejectedAttemptCount`，初版写成 `rejectedAttempts`。
   **修复后**：Div.3 实测 10715 条记录取到失败次数。

2. **罚时单位混乱**
   ICPC 赛制的 `penalty` 单位是**分钟**（非秒），而字段名为 `penalty_time_ms`；
   CF 赛制按分数衰减、`penalty` 恒 0 无意义。
   **修复**：ICPC 制 ×60000 换算为毫秒（与牛客对齐），CF 制置 `None`。
   实测最大罚时 46320000 ms（772 分钟）。

3. **`full_score` 在 ICPC 赛制下恒为 0**
   ICPC 制题目无 `points` 字段，`sum(None or 0)` 得 0，是错误值。
   **修复**：题目分值不全时置 `None`。CF 制正常计算，Div.2 实测满分 13500.0。

4. **同一场榜单重复下载两次**
   `fetch_problem_list` 与 `fetch_all_ranks` 各请求一次全量 standings，
   单场 7–9 MB，等于流量与限速开销翻倍。
   **修复**：加会话内缓存，抓完单场立即 `clear_cache` 释放。

5. 顺带确认：匿名 standings **不支持** `from/count` 分页，
   带额外参数返回 `400: available only via anonymous GET requests with no extra parameters`，
   初版注释无误。同时匿名榜只含正式参赛者（`participantType` 全为 `CONTESTANT`），
   `filter_post_contest` 实际不会命中，保留仅为跨平台语义一致。

### 牛客（用户提供的参考脚本，实测仍有两处问题）

1. **`reachTime` 在 ICPC 赛制下不存在**
   周赛（`rankType=WEEKLY`）的 `scoreList` 有 `reachTime`，
   但校赛/联赛（`rankType=ICPC`）**没有该字段**，只有绝对时间戳 `acceptedTime`。
   初版直接取 `reachTime`，导致 ICPC 制比赛所有 AC 记录耗时全为 `None`。
   **修复**：回退用 `acceptedTime - basicInfo.contestBeginTime` 换算为相对赛程毫秒。
   实测河南萌新联赛 1719 条 AC 记录全部拿到耗时。

2. **`max_pages=50` 可能截断大型比赛**
   初版盲目翻页至空页，安全上限 50 页 = 2500 人，超出规模会静默丢数据。
   **修复**：读取首页 `basicInfo.pageCount` 作为权威总页数精确翻页，
   `max_pages=None` 表示抓完整场；显式传值时若不足会打印截断警告。
   实测周赛 Round 155 抓满 22 页 1100/1100 条，与 `rankCount` 完全一致。

3. 次要优化：`problemId → 题号` 由每条线性查找改为预建反向索引（原为 O(n²)）。

## 二·五、rated-only 与排除付费（2026-08-04 二轮）

按需求「只收录三平台 rated 比赛，付费比赛不计入」，实测确定了各平台的判定依据。

### 判定规则

| 平台 | rated 判定 | 付费判定 | 额外请求 |
|---|---|---|---|
| Codeforces | `contest.ratingChanges?contestId=X` 返回 OK 且非空 | 无付费赛，恒 `False` | 每场 1 次 |
| AtCoder | `contests.json` 的 `rate_change != "-"` | 无付费赛，恒 `False` | 0（列表自带） |
| 牛客 | `contest-info` 的 `category` ∈ 官方系列 且 `uid` ∈ 官方账号 | `contest-info` 的 `needCharge` | 每场 1 次 |

三个爬虫统一新增 `check_rated(contest_meta)` 与 `filter_contests(...)`，
比赛字段新增 `is_rated / is_paid / rated_source / rated_comment`，
`run()` 新增 `rated_only=True, exclude_paid=True` 开关（默认开启）。

### 各平台实测

**Codeforces**：全站 2138 场，已结束 2132 场。近 8 场全部 rated；
`2216 Codeforces Round 1092 (Unrated)` 正确判为非 rated。
未结束的比赛 `ratingChanges` 同样返回 FAILED，因此先用 `phase != "FINISHED"` 挡掉，
返回 `is_rated=None` 而非 `False`，避免把新赛误杀。

**AtCoder**：全站 6276 场 → rated 799 场 / unrated 5477 场。
`rate_change` 取值形如 `"~ 1199"`、`"All"`、`"- ~ 1999"`，仅 `"-"` 表示不计分。

**牛客**：日历接口不含 rated / 收费字段，必须逐场请求 `contest-info`。
通过反查若干用户的 `rating-history`（62 场 rated 比赛）归纳出映射：

| category | 主办 uid | 系列 | 计入 rating | 收费 |
|---|---|---|---|---|
| 19 | 919247 | 牛客周赛 | 是 | 否 |
| 9 | 999991351 | 牛客小白月赛 | 是 | 否 |
| 6 | 999991351 | 牛客练习赛 | 是 | 否 |
| 2 | 999991351 | 牛客挑战赛 | 是 | 否 |
| 20 | 999991351 | 暑期多校训练营 | 是 | **随年份变**（2021 免费 / 2026 收费） |
| 21 | 999991351 | 寒假算法基础集训营 | 是 | **收费** |
| 8 | 各校 uid | 校赛 / 自主命题赛 | 否 | 否 |

关键坑：**收费状态同一系列不同年份会变**，不能按系列硬编码，必须逐场读 `needCharge`。
实测 8 场样本过滤后只保留周赛 155、小白月赛 135、挑战赛 90、练习赛 125 四场，
2026 暑期多校与 2022 寒假营因收费被剔除，武汉理工校赛与河南萌新联赛因非 rated 被剔除。

### 重要发现：Codeforces 匿名 standings 会丢人

大场次的匿名 `contest.standings` 返回的人数**显著少于**实际参赛人数，
且是 `ratingChanges` 的严格子集（没有任何人只出现在 standings 里）：

| contestId | 比赛 | standings | ratingChanges | 缺失 |
|---|---|---|---|---|
| 2248 | Round 1113 (Div.2) | 9190 | 13317 | 31% |
| 2244 | Round 1109 (Div.3) | 12173 | 20340 | 40% |
| 2231 | Round 1099 | 10818 | 15009 | 28% |
| 2200 | Round 1084 | 9870 | 14992 | 34% |
| 2150 | Round 1053（小场） | 961 | 961 | 0% |

小场次一致，大场次丢三到四成。如果学生恰好落在被丢的那批里就永久抓不到，
必须换取数路径。因此 `cf_scraper` 新增 **`mode="rating"`（默认）**：

- 题目列表 ← `problemset.problems` 全站索引（一次性拉取后复用，替代每场 9 MB 的 standings）
- 参赛名单 ← `contest.ratingChanges`（完整，含 `rank / oldRating / newRating / delta`）
- 每题明细 ← 仅对本系统注册的学生调 `contest.status?contestId=X&handle=Y`
  （`enrich_ranks_with_details()`，实测能取到 standings 里缺失的 Zhao05 的 A、B 两题 AC）

原 `mode="standings"` 保留，用于小场次或确需全员每题明细的场景。

## 二·六、学校归属改为平台 ID 绑定

按需求「不从比赛中收集学校信息」，三个爬虫的排名 `school` 字段一律置 `None`，
原来的学校来源降级到 `extra` 仅供人工核对：

| 平台 | 原学校来源 | 现处置 |
|---|---|---|
| Codeforces | `party.organization`（个人赛基本为空） | 保留在 `school`（本就近乎全空），不用于绑定 |
| AtCoder | `Affiliation`（约 28% 填写，写法混乱） | `school=None`，移入 `extra.affiliation` |
| 牛客 | 榜单 `school`（用户自填） | `school=None`，移入 `extra.profile_school` |

学校归属统一由用户注册时填写的三平台 ID 决定：
用户注册 → 填写 CF handle / AtCoder ID / 牛客 uid → 填写学校 → 三个 ID 自动绑定到该学校。
爬虫只负责按平台 ID 产出成绩，归属判定完全在业务侧完成。

这样做的好处：口径唯一、可审计、不受平台自填数据质量影响；
代价是未注册的用户不进入学校积分，属于预期行为。

## 三、统一契约（三平台一致）

比赛列表字段：
`contest_id, real_contest_id, name, oj, link, start_time, end_time, duration_minutes`

排名字段：
`rank, uid, user_name, school, team, accepted_count, total_score, full_score,`
`penalty_time_ms, color_level, post_contest_append, score_detail, extra`

题目明细字段（`score_detail[]`）：
`problem, problem_id, accepted, score, failed_count, reach_time_ms, first_blood, post_contest_score`

新增 `extra` 字段承载各平台特有信息，避免语义扭曲：
- Codeforces：`contest_type, participant_type, successful_hacks, unsuccessful_hacks, room, ghost`
- AtCoder：`performance, old_rating, new_rating, rating, is_rated, country, competitions, atcoder_rank`
- 牛客：`rank_type, team_member_uids`

## 四、各平台数据可用性对照

| 字段 | Codeforces | AtCoder | 牛客 |
|---|---|---|---|
| rank | 有 | 有（Place） | 有 |
| uid / user_name | 有（handle） | 有 | 有 |
| school | 空（个人赛无机构） | 部分（约 28%） | 有（几乎全量） |
| accepted_count | 有 | 无 | 有 |
| total_score | 有 | 无 | 有（OI 制） |
| penalty_time_ms | ICPC 制有 | 无 | 有 |
| score_detail | 完整 | 空（端点限制） | 完整 |
| 表现分/Rating | 无（需另请求 user.rating） | 有 | 无（有 colorLevel） |

对排名系统的含义：Codeforces 与牛客可直接算题目级积分；
AtCoder 建议以 `Place` + `Performance` 为积分依据，`Performance` 比名次更能反映实力。

## 五、成本实测

| 平台 | 单场耗时 | 单场流量 | 说明 |
|---|---|---|---|
| Codeforces | 约 5 s | 7–9 MB | 单次全量，受 1 req/2s 限速 |
| AtCoder | 约 8 s（含首次建索引） | 4 MB + 索引 4 MB | 索引会话内复用 |
| 牛客 | 约 3 s/页，1100 人约 65 s | 每页约 140 KB | 50 条/页，人数越多越慢 |

牛客是三者中最慢的，大型比赛（数千人）单场可能需要数分钟，
接入 Celery 时建议单独设队列与超时，避免阻塞其他任务。

## 二·七、作弊账号识别与排除

牛客对判定作弊的选手，会在榜单 `userName` 前拼接标记文案，
这类记录必须排除出积分，否则会严重污染学校排名。

**实测严重程度**：牛客周赛 Round 155 取样前 200 名检出 **11 个**作弊账号，
**其中第 1 名和第 2 名都是作弊账号**；小白月赛 135 前 300 名检出 8 个。
一个学校只要有一个作弊号进榜，总分就会被明显拉高。

### 三平台处理方式

| 平台 | 平台侧行为 | 我们的处理 |
|---|---|---|
| 牛客 | 榜单 `userName` 加「已被标记为作弊」前缀，**记录仍在榜上** | 正则识别 → `is_cheater=True`，入库层强制排除 |
| Codeforces | 判定作弊者直接移出 `contest.ratingChanges` | 我们本来就以 ratingChanges 为准，天然过滤 |
| AtCoder | 判定作弊者被 unrate（`IsRated=false`） | rated 过滤已覆盖 |

CF / AtCoder 的 `parse_ranks` 也输出 `is_cheater` 字段（恒 `False`），
仅为让入库层的三平台契约一致，不需要按平台分支。

### 双层防御

1. **爬虫层**（`NowCoderScraper.detect_cheater`）：识别并打 `is_cheater` 标记，
   `user_name` 剥离前缀便于展示与匹配，原文存进 `extra.raw_user_name` 供审计。
   默认**只标记不丢弃**，保留原始数据可追溯；传 `exclude_cheaters=True` 才直接剔除。
2. **入库层**（`backend/apps/crawler/ingest.py`）：同一套正则再判一次，
   兜住旧版本爬虫产出的、没有 `is_cheater` 字段的 JSON。
   作弊记录**落库但强制** `is_excluded=True, exclude_reason="cheater"`，
   积分引擎只从 `Participation.objects.countable()` 取数，物理上取不到作弊记录。

标记文案历史上有变体，正则同时覆盖中英文方括号与
「该用户已被…」「已被平台标记…」「…，成绩无效」等写法，
并确保不误伤 `【大佬】李四` 这类带方括号的普通昵称。

## 六、待关注事项

1. ~~牛客作弊账号需识别并排除~~ —— **已完成**，见「二·七」。爬虫层打标记 +
   入库层强制排除，双层防御，实测有效。
2. AtCoder 的 `Affiliation` 为用户自填，同一学校可能有多种写法，
   需要做别名归一化后才能按学校聚合。
3. Codeforces 拿不到学校信息，只能靠本地 handle ↔ 学生绑定关系补齐。
4. 三平台均未使用登录态与签名破解，走的都是公开端点，合规风险低；
   限速策略已内置（CF 2.1–3.0s / AtCoder 1.1–2.0s / 牛客 1.5–3.5s）。

## 七、复验方式

```bash
# 字段契约回归（66 项）
python verify_scrapers.py cf     # Codeforces
python verify_scrapers.py at     # AtCoder
python verify_scrapers.py nc     # 牛客（限 4 页快速校验契约）
python verify_scrapers.py page   # 牛客完整翻页（约 65 s）
python verify_scrapers.py        # 全部

# rated / 付费 / 作弊过滤回归
python verify_rated.py cf
python verify_rated.py at
python verify_rated.py nc        # 含作弊识别断言（离线 7 种写法 + 联网实测）
python verify_rated.py all
```

退出码 0 表示全部断言通过，非 0 表示存在失败项并会列出明细。

入库层（Django）的作弊排除另有单元测试：

```bash
cd ../backend && python manage.py test apps.crawler
```
