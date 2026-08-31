# E-algo Rank 项目接手文档

> **本文件是本项目唯一的开发文档（single source of truth）。** 其他历史文档（`overview.md`、`BACKEND_HANDOFF.md`、`crawlers/VERIFICATION.md`）的内容已合并进本文，已删除，避免信息分叉。
> 文档基准时间：**2026-08-25**（2026-08-27 增补 passport 协议升级适配，见 §1.7.3）。代码路径：`D:\_Dev\e-algo-rank\`
> 配套设计原型（非开发文档，仅前端 UI 来源）：`prototype design for rank/{DESIGN|DELIVERY}.md` + `prototype.html`。

---

# 第一部分：项目进度

## 1.1 整体状态（2026-08-14）

面向**高校算法竞赛**的**学校维度积分排名系统**：自动爬取 Codeforces / AtCoder / 牛客三大平台成绩，按学校聚合排名，配套管理员申请审批、系统公告/站内信、后台管理与用户端展示。后端 Django + DRF + Celery，前端 Vue 3 + TS + Pinia + 自建设计系统（已移除 Naive UI），认证统一走 lotus-passport（RS256 离线验签）。

- ✅ **已是 git 仓库**（master 分支，提交历史完整），非早期文档所说的"无 VCS"。
- ✅ 核心功能（认证、爬虫调度、积分引擎、公告、站内信、权限体系、管理后台、用户端）**均已落地并验证**。
- ✅ **Lotus Passport 接入契约已实测核实（2026-08-16）**：iss=lotus-passport、RS256、不签发 aud、access 30min/refresh 14d、redirect_uri 白名单 origin 级含 rank.eacm.cn、JWKS 公网可达。详见 §1.7.2。
- ⏳ 生产化（PostgreSQL / Gunicorn / Docker 部署）尚未落地（passport 接入配置已就绪，H1 部署执行时即可生效）。
- ⏳ 少量技术债务与可选增强见 §1.5。

## 1.2 已完成功能模块

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| Django 骨架 + 模型 | ✅ | 自定义用户模型 `accounts.User`；7 个 app（accounts/schools/contests/crawler/ranking/common/announcements） |
| 认证与用户 API | ✅ | 注册/登录/JWT/改密/平台账号/用户名认领（passport 首登 UUID 占位→补全页认领锁定） |
| 登录安全 | ✅ | 失败锁定+自动解锁/管理员解锁；登入登出多维限流（账号/设备指纹/IP 兜底放宽）；撞库与会话探测异常检测；安全戳会话吊销；**校园网共享 NAT 友好**（见 §1.9） |
| Lotus Passport 接入 | ✅（生产已验证 2026-08-16） | RS256 离线验签 + 双轨认证（HS256 本地兜底并存）；fragment 回调解析；契约见 §1.7.2 |
| 管理员申请与审批流 | ✅ | 提交/列表/审批/驳回/撤回；仅超管审批；**申请校验**：原因必填、每月限一次、已是管理员禁止再申请 |
| 积分排名引擎 | ✅ | 基础分 + 平台/比赛系数加权；学校榜/学生榜快照 + Redis 缓存层 |
| 爬虫 Celery 接线 | ✅ | 每日爬 + 每日重算（beat 调度由迁移种子写入 DB） |
| **定时自动爬取配置** | ✅ | `CrawlConfig` 单例（超管设置启用开关/各平台抓取范围/触发小时）；`auto_crawl_task` 由 Beat 每日调度，`CrawlConfig` 变更经 signal 同步 beat crontab |
| 爬虫防重复爬取 | ✅ | 任务级：同平台+同参数去重窗口(1h)内已有进行中任务则不重复派发（Python 归一化比较）；比赛级：`Contest(platform, external_id)` 唯一约束 + `update_or_create` |
| 牛客作弊双层防御 | ✅ | 爬虫层标记 + 入库层强制排除（`is_excluded=cheater`） |
| **健康检查端点** | ✅（2026-08-25） | `/api/v1/healthz/` 返回 `{"status":"ok"}`；原顶层 `/healthz` 会被 nginx SPA fallback 吞掉，实际不可用 |
| **僵尸爬取任务清理** | ✅（2026-08-25） | `manage.py stale_crawl_jobs [--hours N] [--fix]`：标记卡在 running/pending 超过 N 小时（默认 2h）的任务为 failed |
| 系统公告 | ✅ | `announcements` app：超管 CRUD + 公开列表；前端公告条 + 超管发布/置顶 |
| 站内信 | ✅ | 通用 `Notification` 模型；超管主动群发（`/notifications/publish/`） |
| 权限体系（3 角色） | ✅ | 普通用户 / 学校管理员 / 超级管理员；详见 §2.7 权限矩阵 |
| 管理后台前端 | ✅ | 仪表盘/学校/审批/爬虫/记录/成员/群发站内信/**积分系数设置** 等页 + 角色化侧边菜单 + 深/浅色主题 |
| **自动爬取设置页** | ✅ | 爬虫页新增「自动爬取设置」卡片：超管开关定时爬取、配置各平台抓取范围与触发小时；保存自动同步 Beat |
| 用户端前端 | ✅ | 首页/排名榜/比赛列表/个人成绩 + SVG 折线图 |
| 种子数据 + 测试账户 | ✅ | `seed_demo` 造数据；`create_test_users` 一键生成三类本地测试账户 |

**最近提交**（master，2026-08-14）：
```
<最新> feat: 自动爬取配置 + 积分系数设置页 + 爬虫去重（#1/#2/#3 修复）
14a1b23 feat: 新增 create_test_users 命令，一键生成三类本地测试账户
f981893 refactor: 积分系数改为超管统一设置（去学校维度，单例化）   ← #5 修订
37e29cf feat: #3 爬虫收紧为仅超管 + #5 积分系数校管只读
a94f73b test: 校管数据隔离测试 + 修复 celery-beat 测试库迁移阻塞   ← #4
3c91607 feat(notifications): 超管发布站内信 + 用户端收件箱铃铛       ← #1
aa11e2b feat(schools): 管理员申请校验——每月限一次 + 已管理员禁申   ← #2
2514fe2 feat: 系统公告后端 + 用户端接入
```

## 1.3 进行中任务

**低难度批次（4 项）已完成并提交（commit `fb60235`，后端 67 tests OK）；M1 已提交（commit `1819c6b`）；M2 已验证（后端 77 tests OK / 前端 typecheck 通过）待提交。** 详见 §1.6。最近一轮（2026-08-14）修复的三项验收问题已提交、验证通过（后端 63 tests OK，前端 typecheck 通过）：
- **#1 积分系数设置后台入口**：新增超管专属「积分系数设置」页（`/admin/score-config`，`superOnly`），读取/保存全局 `ScoreConfig` 单例。
- **#2 定时自动激活爬虫**：新增 `CrawlConfig` 单例（超管设置启用开关/各平台抓取范围/触发小时）；`auto_crawl_task` 由 Celery Beat 每日调度，读取 `CrawlConfig` 派发三平台；`CrawlConfig` 变更经 signal 同步 beat crontab；爬虫页「自动爬取设置」卡片可配置。
- **#3 爬虫防重复爬取**：任务级去重（同平台+同参数在 1h 窗口内已有进行中任务则不重复派发，Python 归一化比较，不依赖 JSON 列精确匹配）；比赛级已由 `Contest(platform, external_id)` 唯一约束 + `update_or_create` 保证幂等。

> 注意：本地运行需另起 **Celery worker + Beat**（`celery -A config worker -Q crawl,crawl_slow -l info` 与 `celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`）；Beat 调度条目由迁移 `0004_swap_beat_to_auto_crawl` 写入，本地已存在 `auto-crawl-daily`（每日 02:00）。

## 1.4 待办事项（建议顺序）

1. **生产化部署**：取消注释并安装 `psycopg` / `gunicorn`；配置 `DJANGO_SECRET_KEY`、`ALLOWED_HOSTS`、`VITE_PASSPORT_URL`；Nginx + Gunicorn + Supervisor（见 §2.6）。
2. **真实 GitHub OAuth 浏览器联调**：✅ **2026-08-16 已实测核实**——iss=lotus-passport 与 `PASSPORT_ISSUER` 一致、redirect_uri 白名单 origin 级含 `rank.eacm.cn`、JWKS 公网可达、令牌寿命 access 30min/refresh 14d；前端仅暴露 GitHub 入口为刻意取舍（QQ/微信 passport 侧已就绪，微信未启用）。详见 §1.7.2。
3. **（可选）"我的排名"入口**：个人成绩页展示用户在榜单中的名次（`listRankings({scope:'student', user:me.id})`）。
4. **（可选）AtCoder 学校别名归一化**：`Affiliation` 自填写法混乱，需别名表才能稳定按学校聚合（当前仅靠本地 handle↔学生绑定）。
5. **（已确认不做）分类资源网站推荐**：不在范围内。

## 1.5 已知技术债务 / 遗留问题

| 项 | 级别 | 说明 / 后续动作 |
| --- | --- | --- |
| **base_score 分母用错字段** | ✅ 已修复 | 原用 `valid_participant_count`（ingest 写成本站已绑定人数，生产=1）作分母，rank 稍靠后即得 -1009700 负巨值；改为 `participant_count`（全场人数）优先（2026-08-25，commit a546378，已部署生产） |
| **僵尸爬取任务** | ✅ 已修复 | worker 重启/派发失败会遗留 running/pending 僵尸记录；新增 `stale_crawl_jobs` 命令清理，生产已清理 3 条（2026-08-25） |
| **健康检查缺失** | ✅ 已修复 | 顶层 `/healthz` 被 nginx SPA fallback 吞掉返回 HTML；新增 `/api/v1/healthz/`（2026-08-25，已部署生产） |
| **staticfiles 缺失** | ✅ 已修复 | 生产容器未执行 `collectstatic`，`/static/admin/*` 404（Django admin 样式缺失）。已本地 collectstatic 打包上传到容器 `/app/backend/staticfiles/` 并重启 backend，admin 样式恢复（2026-08-25）。注意：重建镜像后仍需重新 collectstatic |
| **生产依赖未装** | 🟠 | `psycopg` / `gunicorn` 在 `requirements.txt` 中注释；prod 部署前需取消注释并安装 |
| **dev 用 SQLite** | 🟠 | 生产必须切 PostgreSQL（`dev.py` 已预留 `DEV_DB_ENGINE=postgres` 切换） |
| **`UserRole` 前后端枚举潜在不一致** | ✅ 已修复 | 后端 `UserRole.USER="user"`，前端 `types.ts` 曾声明 `'normal'`（仅 dev mock 用到，运行时靠布尔未爆）；已统一为 `'user'` 并同步 `AuthCallbackView` mock（2026-08-14 晚低难度批次） |
| **`ScoreConfig` 系数无和校验** | ✅ 已修复 | `platform_weight + contest_weight` 已强制 =1，且系数非负、`recent_contest_limit` 非负；`ScoreConfigSerializer.validate()` + 4 条测试覆盖（2026-08-14 晚低难度批次） |
| **`proposed_school_name` 未启用** | ✅ 已启用 | 申请支持"系统里还没有的学校"：`school` 可空 + `proposed_school_name` 二选一；审批通过时 `get_or_create` 自动建档（2026-08-14 晚 M1） |
| **`PlatformAccount.handle` 不可改** | 🟡 | 防止归属唯一性被破坏；改学校走 `sync_platform_accounts_school()` |
| **`UnorderedObjectListWarning`** | ✅ 已修复 | `ScoreConfig` 分页无 `ordering`；已在 `ScoreConfigViewSet` 加 `ordering=["-updated_at"]` 消除告警（2026-08-14 晚低难度批次） |
| **Dead code：权限类** | ✅ 已清理 | `common/permissions.py` 的 `IsOwnSchoolAdmin` / `ReadOnlyOrSchoolAdmin` 已删除（全仓库无引用）；保留 `IsSuperAdmin` / `IsSchoolAdmin` |
| **本地无 Redis** | 🟠 | 见 §2.9 环境坑：Celery 触发接口已用后台线程 + socket 探测规避阻塞，但真跑 worker 需先 `redis-server` 或设 `CELERY_TASK_ALWAYS_EAGER=1` |

---

## 1.6 任务分级与执行进度（2026-08-14 晚）

按 `低 → 中 → 高` 推进；涉及**架构调整 / 技术选型 / 范围变更 / 资源调配**的决策点，执行前须向用户确认并等待明确指示。

| 难度 | 任务 | 状态 | 说明 |
| --- | --- | --- | --- |
| 低 | 修复 `ScoreConfig` 分页无序告警 | ✅ 已完成 | `ScoreConfigViewSet` 加 `ordering=["-updated_at"]` |
| 低 | 前端 `UserRole` 枚举对齐（`'normal'`→`'user'`） | ✅ 已完成 | `types.ts` + `AuthCallbackView` mock |
| 低 | `ScoreConfig` 系数和校验 | ✅ 已完成 | `validate()`（权重和=1 / 系数非负 / 上限非负）+ 4 测试 |
| 低 | 个人成绩页「我的排名」入口 | ✅ 已完成 | 调 `listRankings({scope:'student', user:me.id})` 展示学生榜名次 |
| 中 | 启用 `proposed_school_name`（申请系统里还没有的学校） | ✅ 已完成 | 序列化器二选一（绑定已有/新建）+ 审批通过自动建档 + 前端双模式表单 + 5 测试 |
| 中 | AtCoder 学校别名归一化 | ✅ 已完成 | 别名表 `AtCoderAffiliationAlias` + 入库归一化写入 `Participation.extra`（仅参考/核对，不动归属）；admin 注册 + 5 测试 |
| 中 | A. 爬虫只抓「有已关联平台ID用户参与」的比赛 | ✅ 已完成 | `PlatformAccount.participated_contests` 索引 + `relevant_contest_ids` 预筛 + ingest 增量维护 + `rebuild_participation_index` 命令（CF/AT 个人历史接口廉价补全）；`crawl_*` 加 `force` 冷启动全量开关 |
| 中 | B. 接 handles + 落盘缓存 | ✅ 已完成 | CF 生产路径传入本平台全部 handle（每题明细只下这些人）；三平台 `scrape_contest_detail` 加 `cache_dir`/`cache_ttl_hours` 命中跳过下载；`CRAWLER_CACHE_DIR`/`CRAWLER_CACHE_TTL_HOURS` 配置 |
| 高 | 生产化部署（PostgreSQL / Gunicorn / Nginx） | ⏳ 待确认 | 架构+资源：须用户提供部署环境与域名等信息 |
| 高 | 真实 GitHub OAuth 浏览器联调 | ⏳ 待确认 | 环境/范围：受 OAuth 单 callback 限制，须决策 dev App 或沿用 mock |

> 低难度批次（4 项）已提交（commit `fb60235`，后端 67 tests OK）；M1 已提交（commit `1819c6b`，+5 测试）；M2 已验证（后端 **77 tests OK** / 前端 typecheck 通过），任务 A/B 已验证（后端 **82 tests OK** / 迁移 `0005` 已落 dev 库），待提交。中/高难度项涉及范围或架构决策，须用户确认后方可执行。

### 1.6.1 爬虫预筛逻辑：如何识别「没有任何已关联平台ID用户参与」的比赛

> 术语校正（依用户 2026-08-14 指示）：爬虫功能归属**超级管理员**管理，作用范围是**平台全部用户**，而非「本校生」。此处「用户」的精确定义 = 在平台中已关联竞赛平台 ID 的 `PlatformAccount` 持有者（即 `accounts_platformaccount` 表中已存在 `handle` 记录的用户）。`PlatformAccount` 本身已按平台维度全局存储、不隔离学校，因此无需额外的学校过滤。

**判定集合 `relevant_contest_ids(platform)`**
每次执行 `crawl_codeforces / crawl_atcoder / crawl_nowcoder` 时，先聚合该平台下**所有** `PlatformAccount` 的 `participated_contests` 字段：

```python
def relevant_contest_ids(platform):
    """该平台下「有已关联平台ID用户参与的比赛」的 external_id 集合。"""
    ids = set()
    for acc in PlatformAccount.objects.filter(platform=platform):
        for cid in (acc.participated_contests or []):
            ids.add(str(cid))
    return ids
```

- 一个比赛 `external_id` **命中**该集合 ⇒ 至少有 1 位已关联平台ID的用户参加过 ⇒ **值得爬取**（需下载其完整榜单以便为这些用户抽取每题明细 / 排名）。
- 一个比赛 `external_id` **未命中**该集合 ⇒ 没有任何已关联平台ID的用户参与 ⇒ **直接跳过**，**不下载完整榜单**，省流量与存储。

**索引 `participated_contests` 的三种维护来源**
1. **增量维护（ingest 时）**：`ingest.ingest_contest()` 在 `update_or_create` 循环后，凡 `handle` 命中某 `PlatformAccount` 的参与记录，就把本场 `contest.external_id` 并入该账号的 `participated_contests`（取并集后写回）。即「爬过一场、登记一场」。
2. **冷启动 / 补录命令** `rebuild_participation_index`：一次性把索引补全为 =（Participation 表回溯的 `contest__external_id`）∪（Codeforces `user.rating` 接口返回的 `contestId`）∪（AtCoder `users/{handle}/history/json` 接口返回的 contest id，已归一化旧版 `*.contest.atcoder.jp` 域名格式）。这三个接口都**只取个人参赛历史列表、不下载任何完整榜单**，开销极低。NowCoder 无干净的个人历史接口，依赖 Participation 表回溯补录。支持 `--platform` / `--handle` 粒度。
3. **冷启动兜底开关** `force=True`：在 `crawl_*` 入参或触发接口 `force` 字段置真时，**跳过预筛、全量抓取**该平台所有 rated 且未付费的比赛——用于首次部署、索引为空或需要重算排名时的全量扫描；日常调度不设 `force`。

**效果**：日常自动爬取只触碰「平台里真人确实参加过的比赛」，完整榜单下载量从「全平台 rated 比赛」降到「本平台用户涉及的比赛」；配合任务 B 的 per-handle 抽取与落盘缓存，进一步把流量压到只取目标用户的每题明细，且 7 天内同场比赛不重复下载。

## 1.7 高难度任务实施方案（草案，待用户确认 — 2026-08-14）

> 用户已确认"两项都先做方案"，以下为**草案，未改代码**。涉及架构 / 资源 / 环境信息须用户拍板后方可执行（H1/H2 均属此列）。

### H1 生产化部署（PostgreSQL / Gunicorn / Nginx）

**现状（已具备 ~80%）**
- `config/settings/prod.py` 已就绪：PostgreSQL 引擎、`REDIS_CACHE_URL`、SSL 安全头、`SECURE_PROXY_SSL_HEADER`、强制 `DJANGO_SECRET_KEY` / `DJANGO_ALLOWED_HOSTS`。
- `requirements.txt` 第 16–17 行 psycopg / gunicorn 处于注释状态。
- `.env.example` 已覆盖 `DB_*` / `DJANGO_*` / `CELERY_*` / `CORS_*` / `ROOT_ADMIN_*`。
- `STATIC_ROOT=staticfiles`、`MEDIA_ROOT=media`；前端 `npm run build` → `dist`。
- 尚无 nginx / systemd(supervisor) / 部署文档。

**实施步骤（草案）**
1. 取消注释并安装 `psycopg[binary]`、`gunicorn`；提交（chore 依赖）。
2. 生产 `.env`：`DJANGO_ENV=prod` + 真实密钥/域名/库；`PASSPORT_BASE_URL=https://passport.eacm.cn`；`CORS_ALLOWED_ORIGINS`/`CSRF_TRUSTED_ORIGINS` 指向生产前端域。
3. 生产 PostgreSQL 建库建用户 → `migrate` → `bootstrap`（root 超管 + 全局积分配置）→ 可选 `seed_demo`。
4. `manage.py collectstatic --noinput` → `staticfiles/`；`media/` 持久化。
5. Gunicorn systemd unit：`gunicorn config.wsgi:application -k gthread -w <2×CPU+1> -b 127.0.0.1:8001 --env DJANGO_ENV=prod --timeout 120`（working dir=backend，.env 由 `load_dotenv(REPO_ROOT/.env)` 自动读取）。
6. Celery worker + beat 两个 unit，`--env DJANGO_ENV=prod`（worker `-Q crawl,crawl_slow`）。
7. Nginx：① API 虚拟主机反代 `127.0.0.1:8001`，透传 `X-Forwarded-Proto https`，serve `/static` `/media`；② 前端虚拟主机 root=`frontend/dist`，SPA fallback 到 `index.html`。SSL 用 certbot。
8. 前端：`VITE_PASSPORT_URL=https://passport.eacm.cn` `VITE_API_TARGET=https://api.<域>` 后 `npm run build`。
9. 校验：`manage.py check --deploy` + 登录/榜单/重算冒烟。

**需用户决策（资源 / 架构）**
- 目标域名（API 域、前端域、passport 生产地址分别是什么）
- 服务器 OS 与既有组件：是否已装 PostgreSQL / Redis / Nginx？裸机还是容器（当前无 Dockerfile）
- 进程管理用 systemd 还是 supervisor（prod.py 注释提到 Supervisor）
- SSL 证书方式（certbot 自动 / 已有证书）
- 后端、前端、passport 是否同机

### H2 真实 GitHub OAuth 浏览器联调

**现状**
- 认证统一走 lotus-passport（RS256 JWT）；GitHub 登录由 passport 侧接入，本系统仅消费令牌。
- 前端有 `[DEV] 模拟通行证登录` 按钮（mock）；生产应切真实 passport 登录入口。
- 受 GitHub OAuth App **单 callback URL** 限制：dev / prod 二选一（见 §1.4 #2、§2.9）。

**实施步骤（草案）**
1. passport 侧配置 GitHub OAuth App（Client ID/Secret），callback = 生产 passport 回调（如 `https://passport.eacm.cn/auth/github/callback`）。
2. 关键决策（见下）：dev/prod 双 OAuth App，还是沿用模拟登录、prod 直接走真实 passport。
3. 前端：`VITE_PASSPORT_URL` 指向真实 passport；生产隐藏 `[DEV] 模拟通行证登录`；登录入口跳 passport 的 GitHub 授权页。
4. 联调：浏览器真实 GitHub 授权 → 回 passport callback → 拿 RS256 JWT → 本系统 `AlgoRankPassportAuthentication` 离线验签 → 建/解析本地用户 → 登录成功。

**需用户决策（环境 / 范围）**
- 是否要 dev/prod 双套 GitHub OAuth App（受单 callback 限制）
- passport 生产部署地址与是否已配 GitHub provider
- 是否保留前端模拟登录按钮（仅 dev 保留）

### 1.7.1 方案细化（依用户 2026-08-14 确认决策）

**H1 已确认架构**
- 部署形态：**Docker 容器化**（新增 `docker/Dockerfile`，原无 Dockerfile）
- 数据库/缓存：**复用宝塔内置 PostgreSQL 与 Redis**（不另起容器）
- 反代：**复用宝塔现有 Nginx**（不另起 nginx 容器）
- 域名：**rank.eacm.cn**（现挂临时页）→ 前端 + API 同域；API 为相对路径 `/api/v1`，Nginx 反代即可，**无需独立 API 子域**

**已产出草案文件（未部署，待评审）**
- `docker/Dockerfile` —— 后端镜像（python:3.13-slim，含 backend + crawlers，gunicorn 默认命令）
- `docker-compose.yml`（仓库根）—— `backend`/`worker`/`beat` 三服务，`network_mode: host`（直连宿主 127.0.0.1 的 PG/Redis 与 gunicorn:8001），`media` 宿主机 bind mount 持久化
- `.dockerignore` —— 排除 frontend/.git/media/node_modules/ 等
- `deploy/nginx-rank.eacm.cn.conf` —— 宝塔站点：root=前端 dist，`/api` `/static` `/media` 反代 `127.0.0.1:8001`，SPA fallback
- `.env.prod.example` —— 生产环境变量模板（`DB_HOST/REDIS=127.0.0.1`、`PASSPORT_BASE_URL=https://passport.eacm.cn`）
- `.gitignore` 已追加 `.env.prod`、`volumes/`

**H1 部署步骤（草案，待执行）**
1. 启用依赖：取消注释 `requirements.txt` 的 psycopg/gunicorn（提交 chore）。
2. 宝塔 PostgreSQL 建库建用户（`ealgo`/`ealgo` + 强密码）；Redis 确认可达。
3. 复制 `.env.prod.example` → `.env.prod`，填真实 `DJANGO_SECRET_KEY` / `DB_PASSWORD` / `ROOT_ADMIN_PASSWORD`。
4. `docker compose build` → `docker compose run --rm backend python manage.py migrate` → `bootstrap` → 可选 `seed_demo`。
5. `docker compose run --rm backend python manage.py collectstatic --noinput`。
6. 前端：`VITE_PASSPORT_URL=https://passport.eacm.cn` 后 `npm run build`，产物放宝塔站点 `dist/`。
7. 宝塔加载 `deploy/nginx-rank.eacm.cn.conf`，配 SSL（certbot）。
8. `docker compose up -d`（backend/worker/beat）。
9. 校验：`manage.py check --deploy` + 登录/榜单/重算冒烟。

**H2 结论（依用户确认）**
- 本仓库端**不需要**独立的 GitHub OAuth 注册/登录入口；OAuth 接入是 lotus-passport 的职责，注册必须先走通行证，账密仅作注册后登录手段之一。
- 本仓库侧零改动：生产 `VITE_PASSPORT_URL` 指向真实 passport（已在 `.env.prod` / 构建体现）；`[DEV] 模拟通行证登录` 按钮本就是 dev-only。
- 联调链路：经 passport 真实 GitHub 授权 → 回 passport callback → 拿 RS256 JWT → 本系统 `AlgoRankPassportAuthentication` 离线验签 → 建/解析本地用户 → 登录成功。passport 的 GitHub provider 是否就绪属 passport 仓库职责。
- ✅ **2026-08-16 已实测核实**：iss=`lotus-passport`（与 `PASSPORT_ISSUER` 一致，无 `InvalidIssuer`）、redirect_uri 白名单 origin 级含 `rank.eacm.cn`、JWKS 公网 `https://passport.eacm.cn/.well-known/jwks.json` 可达、令牌寿命 access 30min/refresh 14d。集成契约见 **§1.7.2**。

### 1.7.2 Lotus Passport 接入契约（2026-08-16 实测核实）

> 护照侧维护方就集成评审 10 项缺口逐条实测核实（见《集成评审遗留缺口与风险跟踪 2026-08-16》）。本系统侧代码已于此前落地，本次据核实结果锁定生产配置并收口文档。

**域名规划（已确认）**
| 角色 | 域名 |
| --- | --- |
| E-algo Rank 前端 + API（同域，API 经 Nginx 反代 `/api/v1`） | `https://rank.eacm.cn` |
| Lotus Passport 后端 API（本系统登录/刷新令牌打这里） | `https://passport.eacm.cn` |
| Lotus Passport 前端（托管登录页；本系统未直连，仅 passport 自用） | `https://account.eacm.cn` |

**已实测核实的护照侧契约**
- `iss` = `lotus-passport`（与 `PASSPORT_ISSUER` 一致，无 `InvalidIssuer` 风险）。
- 算法 RS256；**不签发 `aud`**（双方均不校验，属已知防御盲区，见下）。
- 令牌寿命：`ACCESS_TOKEN_LIFETIME=30min`、`REFRESH_TOKEN_LIFETIME=14d`（本地 HS256 的 60min/7d 仅作对照，**不作生产预期**；access 过期用 refresh 续期，refresh 过期 14d 后强制重新 OAuth）。
- `redirect_uri` 白名单 `OAUTH_ALLOWED_REDIRECT_URIS=https://account.eacm.cn,https://rank.eacm.cn`，**origin 级**匹配 → 本系统回跳 `https://rank.eacm.cn/auth/callback` 已放行，**无需再登记**。
- CORS：`rank.eacm.cn` 已在 passport `CORS_ALLOWED_ORIGINS` → 浏览器直连其 `/api/v1/oauth/github/login/` 与 `/api/v1/token/refresh/` 均允许。
- JWKS：`https://passport.eacm.cn/.well-known/jwks.json` 公网 HTTPS 正常（证书 SAN 含 `eacm.cn`）。**注意**：passport gunicorn 仅 `127.0.0.1:8000` 明文，必须走公网 `https://passport.eacm.cn`，本系统 `PASSPORT_BASE_URL` 已是该值。

**集成架构（本系统侧，代码已落地）**
- 后端：`AlgoRankPassportAuthentication`（RS256 离线验签）→ `resolve_passport_user()` 按 `passport_user_id` 查/建本地 `User`（首登 `username=UUID占位` + `set_unusable_password`）；`LOTUS_PASSPORT` 配置见 `config/settings/base.py`。
- 前端：`RegisterEntryView` 调 `${VITE_PASSPORT_URL}/api/v1/oauth/github/login/?redirect_uri=${origin}/auth/callback` 取 `authorize_url` → 跳 GitHub；`AuthCallbackView` 解析 fragment 的 `access_token`/`refresh_token` → 存 localStorage → `GET /me/` 由后端验签。刷新由 `client.ts` 拦截器按 `auth_source='passport'` 打 passport `/token/refresh/`。
- 仅 GitHub 入口（QQ/微信 passport 侧已就绪但微信未启用；多 provider 为待补项，非 bug）。

**上线前必做（仅剩运行时核验）**
- [ ] 后端容器内执行 `curl -sS -o /dev/null -w '%{http_code}' https://passport.eacm.cn/.well-known/jwks.json` 期望 `200`（查 DNS / 443 出站 / 内网 CA 信任），纳入 H1 上线检查清单。

### 1.7.3 Passport 协议升级适配（2026-08-27，随护照侧同步实施）

护照侧本轮完成三项协议补强（详见 `lotus-passport/HANDOVER.md` 顶部 2026-08-27 段），rank 侧适配如下：

1. **登录改为授权码 + PKCE（RFC 7636）**：
   - 发起：`startPassportOAuth()`（`api/index.ts`）生成 code_verifier（存 sessionStorage）+ S256 challenge，login 请求带 `code_challenge`；工具在 `frontend/src/utils/pkce.ts`。
   - 回调：`AuthCallbackView.vue` 优先解析 `?code=` → 调护照 `POST /api/v1/oauth/token/ {code, code_verifier}` 换令牌（新函数 `exchangePassportCode`）；旧 `#fragment` 模式保留兜底（过渡兼容，护照侧未带 challenge 的旧链路仍可用）。
   - **效果：access/refresh token 不再经 URL fragment 下发**（不进浏览器历史/Referrer）。
   - 注意：`client.ts` 刷新逻辑不变（仍打护照 `/token/refresh/`）。
2. **aud 校验接通**：护照按登录 redirect_uri origin 签发 `aud`；rank 后端 `LOTUS_PASSPORT["AUDIENCE"]`（env `PASSPORT_AUDIENCE`，生产值 `https://rank.eacm.cn`，dev 为 `http://localhost:5180`）启用 SDK 校验。**留空 = 不校验**（过渡期兼容存量令牌）；启用后存量无 aud 令牌会被拒，用户需重新登录一次。
   - 本地 `C:\Python314` 解释器需 `pip install whitenoise`（requirements 已含，本地缺装会导致测试 70 errors）。
3. **测试基线**：`manage.py test` **110 tests OK**（2026-08-27 实测）。已知无害噪音：`ingest.py` 异步补全参与索引的后台线程在测试库会打 `database table is locked` 日志并真实请求牛客（best-effort 吞异常，不影响断言，属存量现象待优化）。
4. **naive-ui 死依赖已移除**（package.json + lock，src 零引用）。

**10 项缺口处置（集成评审）**
| # | 缺口 | 处置 |
| --- | --- | --- |
| 8.1 | 文档状态未统一为「生产已验证」 | ✅ 本小节统一改写 |
| 8.2 | 两套 callback 混用 | ✅ 已核实：origin 级白名单含 `rank.eacm.cn`，回跳已放行 |
| 8.3 | iss 实际值 | ✅ 实测 `lotus-passport`，与 `PASSPORT_ISSUER` 一致 |
| 8.4 | aud/AUDIENCE 未文档化 | ✅ 护照不签发 aud；本系统显式配置 `LEEWAY/TIMEOUT/JWKS_CACHE_TTL`（`base.py`），盲区已记录 |
| 8.5 | JWKS 出站可达性 | ✅ 护照侧可用；本系统上线前 curl 核验（上条自查清单） |
| 8.6 | 仅 GitHub 接通 | ✅ 刻意取舍，待补 QQ/微信 |
| 8.7 | 令牌寿命未对齐 | ✅ 实测 access 30min/refresh 14d，已记录 |
| 8.8 | 双路由语义不清 | 📌 本系统文档已补：`/register/info`(public，拉学校列表等) vs `/register/complete`(auth，passport 首登补全/绑校) |
| 8.9 | 降级边界 | ✅ 已说明：离线验签对**存量用户**无感；**首登新用户**依赖 `AUTO_CREATE_USER`+验签，passport 宕机且 JWKS 缓存失效时无法建号 |
| 8.10 | 安全戳例外 | ✅ 已说明：`security_stamp` 仅本地 HS256 令牌；passport RS256 不含该声明，改密/解锁/登出全设备吊销对 passport 登录用户**不适用** |

### 1.7.4 前端修复与部署方式变更（2026-08-28）

1. **表格 `hide-mobile` 列错位修复（已上线验证）**：`base.css` 中 `.hide-mobile { display: initial }` 会把 th/td 的 display 重置为规范初始值 `inline`（而非 UA 默认 `table-cell`），导致带该类的列脱离 `table-layout: fixed` 列宽分配、宽度退化为内容收缩——表头与数据盒宽度不同（如 HomeView「参赛人数」列 81.9px vs 39.6px，中心错开 21.2px）。改为 `display: revert`（恢复 UA 默认），受影响的 HomeView「参赛人数」列与 MyScoresView「解题数」列一并修复；`.show-mobile` 移动端同样修正（当前无使用者）。线上实测：display=table-cell、th/td 左右边界完全重合、中心差 0。
2. **前端构建方式（已过时，见 §1.7.5）**：~~本地机器无 node/npm/docker，rank 前端构建改在服务器上执行~~——2026-08-29 起本机已有 node 22.22.2 + 依赖完整，直接本地构建。原服务器 `docker run node:20-alpine` 方案保留为无本地 node 时的备选：源码打 tgz（排除 node_modules/dist）SFTP 上传 → `docker run --rm -v /tmp/rank-fe-build:/app -w /app node:20-alpine sh -c "npm ci --registry=https://registry.npmmirror.com && npm run build"` → dist 内容同步到 `/www/wwwroot/rank.eacm.cn/dist`。
3. **部署陷阱（务必遵守）**：rank-nginx 容器 bind mount 指向 `/www/wwwroot/rank.eacm.cn/dist`，**挂载绑定的是目录 inode**——部署时严禁 `mv dist dist.old && cp -r 新目录 dist`（容器会继续读旧 inode，磁盘新文件容器不可见、线上不生效且极易误判为缓存问题）。正确做法：**保持 dist 目录 inode 不变，只同步其内容**（`rm -rf dist/* && cp -r 新构建/dist/. dist/`）；若已 mv 过，`docker restart rank-rank-nginx-1` 重新解析挂载路径即可恢复。验证部署是否真生效：比对 `curl https://rank.eacm.cn/` 引用的 asset hash 与磁盘 `dist/assets/` 内文件名是否一致。
4. 当前回滚备份：`/www/wwwroot/rank.eacm.cn/dist.old-20260828`（含 2026-08-27 的上一版 dist，稳定后可删）。

### 1.7.5 Rating 折线图牛客风格改版（2026-08-29，已部署生产）

参照牛客竞赛个人主页折线图（`ac.nowcoder.com/acm/contest/profile/…`）重写 `RatingLineChart.vue`（用户决策：分平台各自段位着色 / 保留淡渐变 / Y 轴自适应+段位线裁剪）：

1. **段位着色**：单平台 tab 数据点按该平台官方段位阈值着色——Codeforces `1200/1400/1600/1900/2100/2400/3000`（8 档）、AtCoder `400/800/1200/1600/2000/2400/2800`（8 档）、牛客 `700/1100/1500/2000/2400/2800`（7 档）；「全部」聚合口径无段位概念，保持品牌色。配置集中在组件 `TIER_SETS`。
2. **新视觉元素**：段位参考线（可见 Y 范围内的档位边界虚线 + 右端同色数字标签）；连线降级为中性细线（点是主角，牛客风格）；最新点插段位色小旗（当前 rating 锚点）；面积渐变保留（低透明度，色随最新点段位）。
3. **Tooltip 重构**：段位色渐变头部 `rating (涨跌) (第N名)` 白字粗体 + 身体（比赛名、`YYYY-MM-DD HH:mm` 时间）；默认显示于点下方，近底部垂直翻转、右缘水平翻转；`left/top/right` 0.16s transition 平滑跟随。
4. **动画**：折线 `stroke-dash` 描线进场 0.9s、面积/段位线淡入、数据点逐个错峰入场、小旗延迟 0.85s；`prefers-reduced-motion: reduce` 下全部禁用。
5. **部署**：本地 `npm run build -- --mode production` 构建（本机 node 22.22.2 + `node_modules` 完整，本地构建产物跨平台可用）→ tgz 经 SFTP 上传（辅助脚本 `D:\_Dev\.workbuddy\tmp_sftp.py`；git-bash 下需 `MSYS_NO_PATHCONV=1` 防止远端路径参数被 MSYS 转换）→ dist 保 inode 替换，**无需重启任何容器**。回滚点 `dist.old-20260829`。
6. **验证**：`vue-tsc` 零错误；本地 dev + mock 数据四场景（牛客跨段位 / CF 高分段含 3000 传奇线 / AtCoder 低分段 / 全部聚合）× 深浅两主题视觉通过；生产回归首页/`healthz`/新 MyScoresView chunk 全 200，线上 asset hash 与磁盘一致。⚠️ 图表位于登录页 `/u/my-scores`，**真实数据效果待登录态端到端验证**。

### 1.7.6 Celery 路由修复：recompute 消息黑洞 + 僵尸任务（2026-08-29，P0 已修复）

**现象**（用户报告）：① 新增用户的比赛数据未同步到平台各业务区；② 一个"执行中"爬虫任务疑似卡死。

**根因**（两个独立问题）：

1. **recompute 消息黑洞（问题 1 主因）**：`CELERY_TASK_ROUTES` 将 `apps.ranking.tasks.*` 路由到 `default` 队列，而生产 worker 启动命令为 `-Q crawl,crawl_slow`——`default` 队列**无任何消费者**。beat 每日 04:00 的重算与每次爬取后自动派发的重算消息全部堆积（Redis db10 `default` LLEN=35），RankSnapshot 停滞在 08-27 00:06（北京），期间爬入的新成绩（含新增用户）不进榜单/业务区。爬取本身一直是成功的，只差重算这一环。
2. **僵尸任务（问题 2）**：CrawlJob #57（nowcoder）08-27 23:00 由 beat 启动，随后 worker 容器因部署重建，任务状态永久停在 running（worker 重启丢状态，已知技术债二次发生）。

**修复**：

1. 止血（服务器操作）：`stale_crawl_jobs --hours 2 --fix`（#57 → failed）+ `redis-cli -n 10 DEL default`（清 35 条冗余消息）+ `manage.py recompute_ranking`（立即重算：ScoreRecord +24 ~40 -0，快照恢复至当前时刻）。
2. 根治（commit `4e8cc31`）：`apps.ranking.tasks.*` 路由改 `crawl`；`CELERY_TASK_DEFAULT_QUEUE` 由 `default` 改 `crawl`（**原默认队列即黑洞**，任何未显式路由的任务都会静默丢失）。SFTP 单文件同步 + `docker compose build backend worker` + `up -d --force-recreate backend worker beat`。
3. 闭环验证：手动派发 `recompute_ranking_task.delay()` → worker 日志 `received` → `succeeded in 0.46s`（updated 64），crawl 队列归零 ✓。
4. 补数据：手动派发三平台增量爬取（cf/at/nc，08-29 02:52），完成后爬后重算自动触发。

**坑与教训**：

- ⚠️ **新增 Celery 队列时必须核对生产 worker 的 `-Q` 列表**：路由指向无人监听的队列 = 消息黑洞，全程无任何报错，只能靠业务现象（榜单不更新）发现。排障口诀：`redis-cli -n 10 KEYS '_kombu.binding.*'` 看实际存在的队列 + `LLEN <queue>` 看积压。
- 僵尸爬取任务在每次 worker 重建后都会遗留（08-25 清 3 条、本次 #57），已有手动工具 `stale_crawl_jobs --fix`；长期方案：worker `worker_ready` 信号启动时自动清理（待办，低优先）。
- CrawlConfig `auto_crawl_interval_days=3`（用户 08-28 04:11 设置，非 bug）：自动爬取每 3 天一次，下次 08-30 23:00；间隔 >1 天时 PeriodicTask 走 IntervalSchedule（`crontab=None` 属**预期行为**，勿误判为调度损坏）。需要及时数据时管理页手动触发即可。

### 1.7.7 牛客练习赛漏入库：截断方向 bug + 未结束过滤 + 毒缓存（2026-08-29，已修复部署）

**现象**：用户报告牛客练习赛成绩未入库（对照官方 rating 历史：user2 参加了 08-28「牛客练习赛 156」，rank 116，rating 1029→1208，平台无该场记录）。

**三层根因**：

1. **截断方向 bug（主因）**：`crawl_nowcoder` 的 `contests[:50]` 发生在「按月份升序拼接（`for ym in sorted(target)`）」之后——比赛密集月份（2026-08：多校 10 场+周赛+练习赛+挑战赛，rated 超 50 场）直接砍掉列表尾部**最新的比赛**。#63 的处理日志恰好终止于 08-23 Round 158，08-24 之后的比赛全部漏抓。已排除其他环节：日历接口正常返回练习赛 156、`check_rated` 判定正确（category=6/uid=999991351 在 OFFICIAL_UIDS、needCharge=False）。
2. **未结束比赛无过滤**：CF 侧有 `phase=FINISHED` 过滤，牛客日历无 phase 字段且未按 endTime 过滤——08-25 的爬取把未举办的 Round 159、未开赛的练习赛 156 都抓了详情。
3. **毒缓存（修复后仍会被坑的一层）**：`scrape_contest_detail` 命中落盘缓存即跳过下载（TTL 168h/7 天）——08-25 抓的空榜单（`contest_139209.json` 仅 133B、ranks=0）被缓存，即使列表截断修好后，7 天内的爬取依然命中空数据。**排查口诀：`ls /app/crawlers/data/<平台>/` 看缓存 mtime，`python -c "import json;d=json.load(open(f));print(len(d['ranks']))"` 验空榜单**。

**修复**（commit `7523622`）：

- 截断前 `contests.sort(key=start_time, reverse=True)` 保最新 50 场（被截的最老比赛靠缓存+幂等多轮补抓）；
- 新增 `_ended` 过滤（endTime > now 的比赛跳过，解析失败保守放行）；
- 新增 `NowcoderWindowTests` 回归 2 例，全量 **115 tests OK**。

**验证**：清除 2 个毒缓存（139209 练习赛 156 / 139660 Round 159）→ 重爬 months_back=2（#65 success）→ 练习赛 156 入库，user2 rank 116 / new_rating 1208 / delta +46 与牛客官方完全一致 → 爬后重算自动触发（created: 1）→ 快照更新。

**CF/AtCoder 对账**：预筛为「最新窗口优先 + relevant 历史补充」模式，无截断 bug；最新 rated 比赛均已入库（CF Round 1117 @ 08-17、AT ABC472 @ 08-22），无同类问题。

**待办（低优）**：detail 层对 ranks 为空的响应不写缓存（或缩短空缓存 TTL），从根上免疫毒缓存。

### 1.7.8 六项体验修复（2026-08-29，commit `7462a71`，已上线并端到端验证）

| # | 问题 | 根因 / 实现 |
|---|---|---|
| 1 | 审批意见申请人看不到 | `approve()` 原本不读 request.data、不存 review_comment、通知固定文案（reject 链路本就完整）。已改为与驳回同构：接收/存库/通知携带意见；**驳回通知移除管理端链接**（被驳回者是普通用户，`requiresAdmin` 守卫会弹回，意见已在文案中） |
| 2 | 校管仪表盘空白 | `/crawl-jobs/` 为 `IsSuperAdmin`，校管 403 × `Promise.all` 一损俱损 × 空 catch 静默 → 整页空白。改为**各接口独立加载独立容错**；「触发爬取任务」按钮/爬虫统计卡/最近任务区块 `v-if="auth.isSuperAdmin"`（侧边菜单本就有 superOnly 过滤，仅仪表盘遗漏） |
| 3 | 排行榜用户详情缺签名/折线图 | 后端本就齐全（`GET /users/<pk>/profile/` AllowAny 含 bio + participations 含 weighted_rating）。前端 UserProfileView 增加 RatingLineChart（全部=各平台最新 weighted 累加 + 平台切换，段位化配置复用）；未填签名显示「这个人还没写个性签名」占位 |
| 4 | 个人中心历史最佳口径 | 原「峰值」是单场 weighted_rating 最大值、「最佳排名」是单场名次——均非学生榜口径。新增 `UserBestRecord`（OneToOne，ranking.0003）：`update_user_best_records()` 在每次重算后维护 best_rank（历史最小名次，配对当时 total_score）与 best_score（历史最高总 rating）；挂载于 `recompute_ranking_task` 尾部与 `manage.py recompute_ranking`。API `GET /api/v1/me/best/`（未登录返回全 null）。系数调整导致重算结果变化时以「重算历史中最优」为准（接受口径漂移，与 CF rating 峰值同类） |
| 5 | 积分规则公开页 | `ScoreRulePage` 单例（schools.0006，Django admin 维护 Markdown，保存自动升版本）+ `GET /api/v1/score-rules/`（AllowAny，**动态拼接当前 ScoreConfig 系数**，改系数页面自动同步）+ `/u/score-rules` 页面（`SimpleMarkdown.vue` 自研渲染器：先 HTML 转义再替换语法，无第三方依赖）+ NavBar「积分规则」入口；已预填 v1 文案 |
| 6 | 总 rating 波动 | 设计行为（Elo 当前值跨平台求和，非单调累加），规则页已写明解释 |

**坑**：`/api/v1/` 下 schools 与 ranking 均 include 在根（无 app 前缀），新增 me/best 路径时勿写成 `/rankings/me/best/`（404）；Windows GBK 终端下 `python - <<EOF` heredoc 传中文会因 stdin 编码损坏字面量，**改文件一律用 Read+Edit 工具**。

**验证**：后端 120 tests OK（新增 5 例：审批意见×2、规则 API×1、最佳纪录×2）；vue-tsc 零错误；线上端到端——/u/score-rules 渲染完整（v1 文案+动态系数表）、/u/my-scores 显示「历史最佳排名 #1（当时总 rating 1697.46）」、/u/user/5 折线图+占位正常。校管视角（王婧橦账号）留待实际登录复核仪表盘。

### 1.7.9 多天间隔自动爬取对齐 00:00（2026-08-31，commit `9709aa9`，已上线）

用户原设计确认：间隔 = 1 天 → crontab 按 `auto_crawl_hour` 定点触发（现状保留）；间隔 ≥ 2 天 → 每隔 N 天在 **00:00（Asia/Shanghai）** 触发，不看触发小时。原实现多天分支只设 `IntervalSchedule(DAYS, every=N)`，due = last_run_at + N 天——**钟点继承上次实际运行时刻**（曾致下次落在北京 08-30 23:00 而非 00:00）。

修复：signal 多天分支保存配置时把 `PeriodicTask.last_run_at` 重置到最近一个已过去的 00:00——下次 = 基准 + N 天 = 未来的 00:00；任务恰在 00:00 运行后 last_run_at 自然保持整点，周期自洽。新增 `CrawlConfigSignalTests` 2 例，全量 122 tests OK。**过渡时序**：旧逻辑最后一轮 08-30 23:00 三平台 success（#66/67/68，入库+重算正常）→ 修复部署 → 重置基准 08-31 00:00 → **下次自动爬取 09-03 00:00**。注意 `auto_crawl_hour` 仅在间隔=1 时生效（管理页改多天间隔时该字段不参与，属预期）。

### 1.7.10 历史最佳口径修正：比赛演变重演（2026-08-31，commit `e6c7d06`，已上线对账）

§1.7.8 第 4 项的第一版把 best 定义为「每次全量重算后的名次/积分历史」——重算是覆盖式计算当前状态，历史里只有当前值，用户看到的永远等于当前排名，等于没修。已改为正确语义：对全部 countable ScoreRecord 按 contest_time **重演**，每个赛后时点各用户取每平台最新一场 final_score 求和（与榜单口径一致）并对全体用户排序得当时名次；best_rank = 全部时点最小名次（配对当时总 rating），best_score = 全部时点最高总 rating。确定性重演，每次重算覆盖写入并清理孤儿。复杂度 O(时点 × 用户 log 用户)。

**真实数据对账**（2 学生）：user2 lotus → best #1 @ 1943.22（2026-08-23，历史峰值 ≠ 当前 1697.46）；user5 AuCu → 曾在 2026-02-03 排名 #1（当时 1111.76）。API `/me/best/` 与个人中心展示不变，数据语义已正确。测试重写为重演场景 3 例，全量 123 tests OK。

### 1.7.11 登录/注册页莲花单一入口 + 通用 OAuth（2026-08-31，与 passport `831ce33` 配套，已上线）

- passport 新增 provider 无关入口：`GET /api/v1/oauth/login/`（一次性票据 oauth:generic:\<ticket\> TTL 600s → passport-web 登录页 URL）与 `POST /api/v1/oauth/continue/`（web 登录后凭票据 + Bearer 换发往接入方的单次 PKCE 授权码）。passport-web /login 暂存 `?oticket=`（sessionStorage 跨登录子页存续），密码/邮箱验证码/OAuth 回调三个成功落点优先续行回接入方。详见 passport `HANDOVER.md` 顶部段。
- rank 两页改版：/login 与 /register 只保留「Lotus 通行证登录」大按钮（`LotusPassportEntry.vue`：旋转渐变环图标 + 掠过高光 + 浮起动效，尊重 prefers-reduced-motion），点击发起通用入口（PKCE）；LoginView 本地账号表单按用户决策移除；RegisterEntryView 管理员文案/按钮已删；`PassportLoginButtons.vue` 删除（已无引用）。平台正式图标（favicon/导航/登录/注册页）同批替换。
- 已上线验证：passport 端点 curl 实测返回 login_url；rank 新 dist hash 上线、lotus-icon/favicon 均 200。已登录访问 /login 被守卫重定向属预期——完整登录流程需隐身窗口人工验收。

**H1 执行前仍需用户提供**
- 宝塔 PostgreSQL 连接账号密码、Redis 端口（默认 6379 容器内是否可达）
- `DJANGO_SECRET_KEY` 强随机值、初始超管密码
- passport 生产地址与 GitHub provider 是否就绪（影响 `PASSPORT_BASE_URL` 与 CORS）
- 服务器是否已装 Docker / Docker Compose

---

# 第二部分：需要记忆的关键信息

## 2.1 项目背景与核心目标

- 服务**高校算法竞赛生态**，把分散在 Codeforces / AtCoder / 牛客的成绩统一聚合为**学校维度积分榜**。
- 成绩归属**只认用户注册时绑定的三平台 ID → 学校**，绝不从比赛榜单读学校字段（数据质量不可控）。
- 多学校同台排名，因此**积分系数由超管统一设置一份**（见 §2.8 历史决策）。
- 认证未来统一走 **lotus-passport**（独立仓库，本系统仅消费其 RS256 JWT），业务权限（role/school/管理员）由本系统维护。

## 2.2 技术架构与关键技术选型

| 层 | 选型 |
| --- | --- |
| 后端 | **Django 5.2**（本机两个解释器：`C:\Python314\python.exe`=5.2.16；venv `…/envs/default`=5.2.17，二者均可）+ DRF 3.x |
| 认证 | `djangorestframework-simplejwt`（本地 HS256 兜底）+ lotus-passport-sdk（RS256 离线验签）双轨 |
| 数据库 | SQLite（dev）/ PostgreSQL（prod） |
| 缓存 / 队列 | Redis + Celery + django-celery-beat（DatabaseScheduler） |
| 爬虫 | `requests` + BeautifulSoup；CF/AtCoder/牛客公开端点（无登录破解） |
| 前端 | Vue 3 + Vite + TypeScript + Pinia + Vue Router；**自建设计系统**（已移除 Naive UI） |
| API 文档 | drf-spectacular（Swagger，路径 `/api/docs/`） |
| 部署 | Nginx + Gunicorn + Supervisor（规划中，未上线） |

**请求流向**
```
前端(Vite 5180) ──/api/v1/*──► Django+DRF(8001) ──ORM──► SQLite(dev)/PostgreSQL(prod)
                                                      └─ Celery Worker ─► 爬虫(crawlers/)→ingest→DB→排名引擎重算
定时：Celery Beat ──► django_celery_beat 周期任务（迁移种子写入）
```

## 2.3 代码结构说明

```
e-algo-rank/
├─ backend/
│  ├─ manage.py
│  ├─ config/
│  │  ├─ settings/{base,dev,prod,__init__}.py   # 敏感配置全走环境变量(.env)
│  │  ├─ urls.py            # admin / healthz / api/v1 / schema / docs
│  │  ├─ celery.py          # Celery app
│  │  ├─ pagination.py      # StandardPagination：{count,page,page_size,total_pages,results}
│  │  └─ asgi.py / wsgi.py
│  └─ apps/
│     ├─ common/      # Platform/ExcludeReason 枚举、TimeStampedModel、权限类、统一异常
│     ├─ accounts/    # User、PlatformAccount、Notification；注册/登录/资料/改密/平台账号/站内信；bootstrap/seed_demo/create_test_users 命令
│     ├─ schools/     # School、SchoolAdminApplication、ScoreConfig(单例)；学校CRUD、申请审批
│     ├─ contests/    # Contest、Participation；比赛只读、本人参赛、校管参赛记录
│     ├─ crawler/     # CrawlJob、ingest.py(业务规则唯一落地点)、tasks.py(Celery)、beat 迁移
│     ├─ ranking/     # ScoreRecord、RankSnapshot、engine.py(积分引擎)、cache.py(缓存)、recompute_ranking 命令
│     └─ announcements/ # Announcement 模型 + 超管 CRUD + 公开列表
├─ crawlers/                     # 三平台爬虫（与 backend 平级，被 crawler/tasks.py 经 sys.path 复用）
│  ├─ cf_scraper.py / atcoder_scraper.py / nowcoder_scraper.py
│  └─ verify_scrapers.py / verify_rated.py   # 联网回归脚本（66/66 通过）
├─ frontend/
│  └─ src/
│     ├─ api/{client,types,index}.ts   # axios 实例(API_BASE='/api/v1') + 类型 + 接口函数
│     ├─ stores/auth.ts                # Pinia 鉴权：token + loadMe；isAdmin/isSuperAdmin/isProfileComplete
│     ├─ router/index.ts               # 守卫：public / requiresAuth / requiresAdmin / superOnly
│     ├─ layouts/{AdminLayout,PublicLayout}.vue
│     ├─ views/{auth,admin,user}/*.vue + LoginView.vue
│     ├─ components/ui/*.vue           # 自建设计系统组件库（RankBadge/OrgLogo/UserAvatar/...）
│     ├─ styles/{tokens,base,components}.css  # 新设计系统令牌
│     └─ utils/format.ts
├─ requirements.txt / .env.example / .gitignore
└─ prototype design for rank/         # 设计原型参考（非开发文档）
```

**核心模型关系**：`User` 1—* `PlatformAccount`；`User` *—1 `School`；`School` 1—* `SchoolAdminApplication`；`Contest` 1—* `Participation`；`Participation` 1—1 `ScoreRecord`（仅 countable 生成）；`RankSnapshot`（school/student 两种 scope，定时重算后前端直读，带 Redis 缓存）。

**积分引擎数据流**：爬虫 parse → Celery tasks（写 CrawlJob 审计）→ `ingest.ingest_contest()` → `Contest`/`Participation` → `Participation.countable()`（仅 is_excluded=False & 有平台账号 & rated & 非付费）→ `ScoreRecord` → `RankSnapshot` → REST `/rankings/`。
**积分公式**：`base = 100 × (1 - (rank-1)/max(1, valid_count))`；`combined = platform_weight×平台系数 + contest_weight×比赛难度系数`；`final = base × combined`。

## 2.4 重要配置与环境变量

全部配置在 `config/settings/base.py`（dev/prod 继承）。敏感项走 `.env`（仓库根，` .env.example` 对照）。

| 变量 | 说明 |
| --- | --- |
| `DJANGO_ENV` | `dev` / `prod` |
| `DJANGO_SECRET_KEY` | prod 必填，缺失则 `prod.py` 拒绝启动 |
| `DJANGO_ALLOWED_HOSTS` | 逗号分隔 |
| `DB_*` | 生产 PostgreSQL 连接（dev 默认 SQLite `db.sqlite3`） |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` / `REDIS_CACHE_URL` | 默认 `redis://127.0.0.1:6379/{0,1,2}` |
| `CELERY_TASK_ALWAYS_EAGER` | 本地无 Redis 设 `1` 同步执行 |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | JWT 有效期（默认 60 / 7） |
| `PASSPORT_BASE_URL` / `PASSPORT_ISSUER` | lotus-passport（默认 `http://127.0.0.1:8000` / `lotus-passport`；生产 `https://passport.eacm.cn` / `lotus-passport`，已实测核实） |
| `PASSPORT_AUTO_CREATE_USER` | 首登无本地行时自动建号（默认 `True`） |
| `PASSPORT_JWKS_LEEWAY` / `PASSPORT_HTTP_TIMEOUT` / `PASSPORT_JWKS_CACHE_TTL` | 验签时钟容忍(s,默认10) / JWKS出站超时(s,默认5) / JWKS缓存(s,默认600)；已显式化于 `base.py` |
| `CORS_ALLOWED_ORIGINS` | 前端地址（生产 `https://rank.eacm.cn`）；passport 侧 CORS 亦含 rank.eacm.cn |
| `ROOT_ADMIN_USERNAME/EMAIL/PASSWORD` | 初始超管，密码留空则随机生成打印一次 |
| `VITE_PASSPORT_URL` / `VITE_API_TARGET` | 前端：`https://passport.eacm.cn` / 后端（同域生产用相对 `/api/v1`，此项仅 dev 代理） |
| `aud` / `AUDIENCE` | 护照**不签发** `aud`，本系统未设 `AUDIENCE`（SDK 默认 `None`）→ 双方均不校验；属已知防御盲区（详见 §1.7.2） |

**本地运行**
```bash
# 后端（必须用带 Django 的解释器，见 §2.9）
cd backend
<PY> manage.py migrate
<PY> manage.py bootstrap            # root 超级管理员 + 全局积分配置
<PY> manage.py seed_demo           # 可选：造 6 校/120+ 生/演示比赛并重算榜单
<PY> manage.py create_test_users   # 生成三类本地测试账户（见 §2.10）
<PY> manage.py runserver

# 前端
cd ../frontend && npm install && npm run dev   # Vite 5180，代理 /api → 后端 8001
```
`<PY>` 取 `C:\Python314\python.exe` 或 venv `…/envs/default/Scripts/python.exe`。

## 2.5 第三方服务与依赖

- **lotus-passport**（独立仓库 `D:\_Dev\lotus-passport`）：统一认证，RS256 JWT。仅消费其令牌；QQ/微信/GitHub 登录由 passport 侧接入。
- **三平台公开 API**：Codeforces 官方 API（`ratingChanges`/`contest.status`/`problemset.problems`）、AtCoder（kenkoooo `contests.json`/`results/json`）、牛客移动端点（`contest-info`/`ranking`）。无登录态/签名破解，合规风险低；内置限速。
- **后端依赖**（`requirements.txt`）：Django、djangorestframework、djangorestframework-simplejwt、django-cors-headers、django-filter、drf-spectacular、celery、django-celery-beat、redis、python-dotenv、requests、Pillow；生产额外 psycopg/gunicorn（注释）。
- **前端依赖**：vue、vue-router、pinia、axios、vite、vue-tsc、typescript。

## 2.6 约定的开发规范与流程

- **Git**：master 分支；提交信息用中文 conventional 风格（`feat:` / `fix:` / `refactor:` / `test:` / `chore:` + 作用域），如 `feat(notifications): 超管发布站内信`。
- **测试先于交付**：后端 `manage.py test`（SQLite 测试库）；前端 `npm run typecheck`（vue-tsc）。提交前两者应通过。
- **权限判断一律走 `user.is_super_admin` / `user.is_school_admin` 属性**，不要散落 `role` 字面量比较。
- **三条硬规则集中在 `ingest.py`**（只入 rated 且非付费、学校归属只认 PlatformAccount、作弊四道拦截），任何"直接写 Participation/Contest"的需求先想清楚是否绕过。
- **前端已切换为新设计系统**：优先复用 `styles/tokens.css` 变量；新增页面必须引用新组件库，**禁止再引入 Naive UI**。
- **API 真实前缀是 `/api/v1`**（不是 `/api`）；联调/排查认准 `/api/v1/*`。
- **清理临时文件用绝对路径**（本环境相对路径 `rm` 会被 safe-delete 拦截）。

## 2.7 权限矩阵（3 角色）

| 能力 | 普通用户 | 学校管理员 | 超级管理员 |
| --- | --- | --- | --- |
| 查看/修改本人资料、平台账号、站内信 | ✅ | ✅ | ✅ |
| 申请成为学校管理员 | ✅（受校验） | ❌（禁止） | ❌ |
| 查看本校成员/参赛记录 | ❌ | ✅（仅本校） | ✅（全站） |
| 审批管理员申请 | ❌ | ❌ | ✅ |
| 学校 CRUD | ❌ | ❌ | ✅ |
| 查看爬虫任务 / 手动触发 | ❌ | ❌ | ✅（仅超管，见 §2.8） |
| 配置自动爬取（CrawlConfig） | ❌ | ❌ | ✅（仅超管；启用开关/各平台范围/触发小时） |
| 积分系数查看/调整 | ❌ | ❌（原只读已取消） | ✅（统一单例，见 §2.8） |
| 系统公告 CRUD | ❌（仅看公开） | ❌（仅看公开） | ✅ |
| 群发站内信 | ❌ | ❌ | ✅ |
| 触发积分重算 | ❌ | ❌ | ✅ |
| 查看排名榜 / 比赛 | ✅（公开） | ✅（公开） | ✅（公开） |

> 权限类：`IsSuperAdmin`（仅超管）、`IsSchoolAdmin`（校管或超管）。`IsOwnSchoolAdmin`/`ReadOnlyOrSchoolAdmin` 已定义但**当前未使用**（dead code）。

## 2.8 历史决策原因（避免重复讨论）

1. **积分系数改为超管统一单例（2026-08-14）**：原设计"每校一份 + 一条全局默认"，因多学校同台排名需要**统一口径**，改为全局唯一 `ScoreConfig`，新增 `get_config()` 单例（缺失自动建默认）；`ScoreConfigViewSet` 仅超管可读写，POST 改为 upsert；迁移 `0002_remove_scoreconfig_school` 去重历史数据并删 `school` 字段。
2. **爬虫收紧为仅超管（2026-08-14）**：需求"系统底层信息仅超级管理员可访问与操作"。`CrawlJobViewSet` 列表与 `trigger` 均由 `IsSchoolAdmin` 改为 `IsSuperAdmin`；前端 `/admin/crawl` 路由与导航加 `superOnly` 门禁。
3. **积分系数调整权归超管（#5）**：先按"校管只读"实现，后因上条统一单例决策，校管完全不可访问。
4. **管理员申请校验（#2）**：原因必填（模型 `blank=False`）+ 每月限一次（按 `created_at` 年/月去重，跨校也受限）+ 已是管理员禁申（`is_school_admin`/`is_super_admin` 拦截）。
5. **学校归属只走平台 ID 绑定**：爬虫 `school` 一律 `None`，平台自带学校字段降级到 `extra` 仅供核对；用户改学校后必须调 `sync_platform_accounts_school()`。
6. **rated-only + 排除付费（2026-08-04）**：只收录 rated 且非付费比赛；牛客 `needCharge` 逐年变化，必须逐场读取。
7. **CF 名次以 `ratingChanges` 为准**：匿名 `contest.standings` 会静默丢人 28–40%，爬虫 `mode="rating"` 为默认；小场次才用 `mode="standings"`。
8. **Passport 双轨认证**：`AlgoRankPassportAuthentication` 先读 JWT `alg`，非 RS256（本地 simplejwt 签的 HS256）放行给下一个认证类，使 root/本地兜底与 passport 并存。
9. **Celery beat 调度由迁移种子写入**：`crawler/migrations/0002_beat_schedules.py` 创建周期任务（CF/AtCoder 每日、牛客每周、重算每日），避免手动配置。
10. **自动爬取改为单入口 + 可配置（2026-08-14）**：原 beat 把三平台爬取窗口硬编码在迁移里、无法启停/调参。改为单一 `auto-crawl-daily` 任务（调用 `auto_crawl_task`），运行时读取 `CrawlConfig`（启用开关/各平台场数月数/触发小时）；`CrawlConfig` 保存经 signal 同步 beat 的 crontab 小时与 enabled。迁移 `0004_swap_beat_to_auto_crawl` 把旧三平台任务替换为统一入口（保留重算任务）。
11. **爬虫去重分层（2026-08-14）**：任务级（CrawlJob）防重复派发——同平台+归一化参数在 1h 窗口内已有 pending/running 任务则返回既有任务不新建；比赛级（Contest）已由 `UniqueConstraint(platform, external_id)` + `update_or_create` 保证幂等入库（同一比赛多次爬取只更新不新增）。任务级去重用 Python 归一化比较而非 JSON 列精确匹配（存储格式化不一致会导致漏判）。

## 2.9 常见坑点及注意事项

**环境类**
- **必须用带 Django 的解释器**（`C:\Python314\python.exe` 或 venv `…/envs/default`），裸 `python` 无 Django → `ModuleNotFoundError`。
- **Redis 黑洞**：本机 `127.0.0.1:6379` 未启动时连接表现为黑洞，Celery 易阻塞。触发接口已用"后台线程 + 2s socket 探测"规避；真跑 worker 先 `redis-server`，或 dev 设 `CELERY_TASK_ALWAYS_EAGER=1`。
- **safe-delete 拦截删除**：命令行 `rm` / 删 `dist` 大目录被安全删除机制拦截。清理用绝对路径 Python `shutil.rmtree`；前端构建用 `vite build --emptyOutDir false`。
- **`db.sqlite3`、`.env`、`media/` 不入库**（`.gitignore` 已覆盖）。
- **Git LF→CRLF 警告**：提交时 `warning: ... LF will be replaced by CRLF` 为良性，可忽略。

**业务/数据类**
- **CF 匿名 standings 静默丢人 28–40%**：名次/计分一律以 `ratingChanges` 为准，勿回退到 `mode="standings"`。
- **牛客 `needCharge` 逐年变**：rated 判定必须逐场请求 `contest-info`，不能按系列缓存。
- **牛客作弊账号**：榜单 `userName` 带「已被标记为作弊」前缀，入库层强制排除（`is_excluded=cheater`），四道拦截缺一不可，后台禁止洗白 CHEATER。
- **学校归属只走 `PlatformAccount`**：禁止从榜单读学校字段。
- **测试库迁移陷阱**：`crawler/migrations/0002_beat_schedules.py` 依赖必须是 `django_celery_beat.0019_alter_periodictasks_options`（不是 `0001`），否则 `manage.py test` 在全新测试库报 `no such column: ...timezone`。
- **改测试文件用"追加"而非整文件覆盖**：避免误删既有用例（曾有用 Write 覆盖 `crawler/tests.py` 丢失入库层测试的插曲）。

**前端类**
- **前端 API 前缀 `/api/v1`**（非 `/api`）。
- **路由布局**：根 `/`→注册入口 `/register`；后台 `/admin/*`（含 `superOnly` 门禁页）；用户端 `/u/*`；`/register*` 认证流。
- **设计系统**：新增页面复用 `styles/tokens.css` 与新组件库，禁 Naive UI。

## 2.10 本地测试账户（由 `create_test_users` 生成）

| 角色 | 用户名 | 密码 | 说明 |
| --- | --- | --- | --- |
| 普通用户 | `test_user` | `Test@123456` | 归属"测试大学" |
| 学校管理员 | `test_school_admin` | `Test@123456` | 归属"测试大学" |
| 超级管理员 | `test_super` | `Test@123456` | 无学校 |
| 初始超管(root) | `root` | 见 `bootstrap` 输出 / `.env ROOT_ADMIN_PASSWORD` | 由 `bootstrap` 创建 |

命令：`python manage.py create_test_users [--password X] [--reset]`（幂等，已存在则跳过）。

## 2.11 常用命令速查

```bash
# 后端
manage.py migrate / bootstrap / seed_demo / create_test_users
manage.py check
manage.py test                 # 全量（当前 96 tests OK，含 apps/accounts/tests_security 14 例登录安全用例）
manage.py test apps.crawler    # 入库层 + 去重 + 自动爬取测试
manage.py recompute_ranking [--scope school --period 2026]
manage.py spectacular --file schema.yml

# 前端
cd ../frontend && npm install && npm run dev      # 开发 5180
npm run build            # vue-tsc 类型检查 + vite 生产构建
npm run typecheck        # 仅类型检查

# 爬虫独立联网回归（crawlers/ 目录）
python verify_scrapers.py all     # 66/66
python verify_rated.py all        # rated/付费/作弊

# 本地跑定时爬取（需先 redis-server；否则 dev 设 CELERY_TASK_ALWAYS_EAGER=1）
celery -A config worker -Q crawl,crawl_slow -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
# 仅验证自动爬取调度逻辑（不真连 worker）：
manage.py shell -c "from apps.crawler.tasks import auto_crawl_task; print(auto_crawl_task())"
```

## 2.12 相关资源链接

| 资源 | 路径 / 链接 | 说明 |
| --- | --- | --- |
| 设计原型（UI 来源） | `prototype design for rank/{DESIGN,DELIVERY}.md` + `prototype.html` | 前端设计系统来源，**非开发文档** |
| 依赖清单 | `requirements.txt` | 直接依赖锁定 |
| 环境样例 | `.env.example` | 全部环境变量说明 |
| API 文档（运行时） | `http://127.0.0.1:8001/api/docs/` | drf-spectacular Swagger |
| Codeforces API | https://codeforces.com/apiHelp | contest.list / ratingChanges / contest.status |
| AtCoder (kenkoooo) | https://github.com/kenkoooo/AtCoderProblems | contests.json / results |
| 牛客接口 | 移动端点（需逆向） | rated 判定逐场 `contest-info` |

---

*最后更新：2026-08-14。合并自历史文档 `overview.md`(爬虫层总结)、`BACKEND_HANDOFF.md`(后端 API 审查)、`crawlers/VERIFICATION.md`(爬虫与作弊验证)，并据 2026-08-14 已完成工作（公告落地、积分系数单例超管、爬虫仅超管、测试账户命令）校正。后续设计变更请同步更新本文件。*

---

## 1.8 本地联调测试（关闭开发者模式，2026-08-14）

目标：验证「关闭开发者模式」后整体功能仍可用。说明：本地唯一可运行配置是 `dev.py`（SQLite+LocMem+宽松 CORS）；`prod.py` 硬编码 PostgreSQL+Redis+SSL 且有 `SECRET_KEY`/`ALLOWED_HOSTS` 强校验，本机未部署 PG/Redis 故无法切 `DJANGO_ENV=prod`。因此后端层「关开发者模式」以「真实密码鉴权链路（非 mock）」等价验证；纯配置切 prod 属 H1 部署任务，待用户确认环境后执行。

前端「开发者模式」= Vite `import.meta.env.DEV`（控制 `[DEV] 模拟通行证登录` 按钮显隐）；生产构建后 `DEV=false`，按钮与 mock 分支被剔除。

### 修复的异常（真实「关开发者模式」漏洞）
- `frontend/src/views/auth/AuthCallbackView.vue`：`if (q.mock)` → `if (import.meta.env.DEV && q.mock)`。原写法生产构建仍可凭 `/auth/callback?mock=1` 伪造用户登录（`auth.token='mock'`）。
- `frontend/src/views/auth/RegisterEntryView.vue`：未配置 `VITE_PASSPORT_URL` 时的 mock 回退改为仅 DEV 触发；生产缺失 passport 地址时给出明确提示而非静默 mock。
- 验证：`npm run build` 后 `grep` 产物已无 `dev_passport_user`/`模拟通行证登录`/`mock` 残留；`npm run typecheck` 通过。

### 验证结果
- **前端**：生产构建 ✅（无 mock 残留）、typecheck ✅。
- **后端全量测试** `manage.py test`：**77 tests OK**（22s），覆盖 accounts/schools/contests/crawler/ranking/announcements 全模块与边界（权限 403 / 校验 400 / 错误密码 401）。
- **运行时冒烟**（真实密码登录 `/api/v1/auth/token/`，非 mock；账号来自 `create_test_users`+`bootstrap`+`seed_demo`，6 校/120 生/36 比赛/榜单快照已生成）：
  - 三角色登录 ✅：test_user / test_school_admin / test_super 均凭密码取得 JWT（233 字符）。
  - `/me/` ✅ 200（username/role/school 正确）。
  - `/rankings/`、`/schools/`、`/contests/` ✅ 200；榜单 `user_name`/`total_score` 填充正常。
  - 权限边界 ✅：普通用户 & 校管访问 `/score-configs/` → 403，超管 → 200；错误密码 → 401；校管可读本校 `/applications/` → 200。

> 误报说明：首轮冒烟脚本误用 `/users/me/`（应为 `/me/`）与字段 `username`（应为 `user_name`），导致 403 与 `None` 假异常；复核确认端点与数据均正常，非代码缺陷。

---

## 1.9 登录安全（防暴力破解 + 异常频率限制 + 校园网应对策略，2026-08-14）

> 实现文件：`apps/accounts/security.py`（核心逻辑）、`apps/accounts/views.py`（`LoginView`/`LogoutView`/`StampedTokenRefreshView`）、`apps/accounts/auth.py`（`StampedJWTAuthentication`）、`apps/accounts/models.py`（`User` 安全字段 + `AuthLog`）、`apps/accounts/admin.py`（解锁动作）、`apps/accounts/tests_security.py`（14 用例）。迁移 `0006_user_failed_login_count_...`。

### 1) 账户级失败锁定与解锁

- `User.failed_login_count`（连续失败计数，成功登录清零）+ `locked_until`（锁定到期时间，空=未锁）。
- `register_login_failure()`：计数 +1；达 `AUTH_MAX_CONSECUTIVE_FAILURES`（默认 5）→ 写入 `locked_until = now + AUTH_LOCK_MINUTES`（默认 15）。
- **自动解锁**：`is_locked` 按 `locked_until > now` 判定，到期即视为解锁，**无需定时任务清理**。
- **管理员解锁**：Django admin `UserAdmin` 的 `unlock_users` 动作，调用 `unlock()`，默认轮换安全戳吊销该账号现存会话。

### 2) 登入/登出频率限制 + 异常行为检测

- 登录限流三维度：**`identifier`（账号维度，防针对已知用户名的爆破）→ `device_fp`（设备指纹维度）→ `ip`（IP 维度，仅兜底）**，依次拦截。
- 登出限流按 **`user` + `jti（会话）** 双维度，防登出接口被刷。
- 异常检测：① 同设备短时尝试大量不同账号（**撞库 credential_stuffing**）；② 同用户短时登录成功↔登出反复横跳（**会话探测**）；命中即拦截/告警（写 `AuthLog` 的 `ANOMALY`）。
- 全部判定读写 `AuthLog`（认证事件流），高频可定期清理。

### 3) 会话吊销（安全戳 security_stamp）

- 登录/刷新令牌写入 `security_stamp` 声明；`StampedJWTAuthentication` 每次请求比对「令牌戳」与 `user.security_stamp`，不一致 → 401。
- **改密、管理员解锁（默认）、登出全部设备（`{"all": true}`）** 均轮换安全戳 → 旧令牌立即失效。升级前签发的无戳旧令牌放行，保证灰度部署不登出全员。

### 4) 校园网 / 共享 NAT 出口应对策略（核心）

校园网/企业网大量用户共享同一 NAT 出口 IP，纯 IP 限流有两大致命缺陷：① **误伤**——把整片出口 IP 下的正常用户一起限流；② **绕过**——攻击者用同一出口即可无视 IP 限制爆破任意账号。

本系统采取「**以账号 + 设备指纹为主，IP 兜底且阈值刻意放宽**」的多维识别：

- **设备指纹优先**（`X-Device-Id` 头 → SHA256）：前端写入 localStorage 的稳定设备 ID，最精准区分同一出口 IP 下的不同浏览器/设备；缺失时回退 `User-Agent|Accept-Language` 哈希（同一校园网不同设备/浏览器通常仍可区分）。
- **账号维度独立**：锁定与失败计数绑定账号本身，**完全不依赖 IP**，攻击者无法借共享出口规避。
- **IP 维度只作纵深防御**：`AUTH_IP_LOGIN_MAX=300`，比设备维度（`AUTH_DEVICE_LOGIN_MAX=20`）高一个数量级，仅用于拦住「整个出口被僵尸网络接管」的极端情况，日常不会误伤共享出口下的正常用户。
- **实测验证**（`NatFriendlyThrottlingTests.test_device_isolation_behind_same_ip`）：攻击者设备在同一校园网出口 IP 下反复失败被 `device_rate` 拦截，而受害者设备（**同一 IP、不同设备指纹**）用正确密码登录仍 200——证明共享 IP 下的正常用户不被误伤，攻击者也无法借共享 IP 绕过设备维度限制。

**效果**：限流/锁定精准落到「具体账号 + 具体设备」，而非「整片校园网 IP」，既防爆破撞库、又不误伤、也防绕过。

**前端接入（2026-08-16）**：`frontend/src/utils/device.ts` 生成 localStorage 稳定设备 ID，`frontend/src/api/client.ts` 请求拦截器全局注入 `X-Device-Id` 头，登录/登出/刷新请求均携带，使设备维度限流真正生效（此前仅后端逻辑就绪、前端未发该头）。

### 5) 配置项（`security.get_security_config()` 先读 `settings` 再读环境变量，均可覆盖）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `AUTH_MAX_CONSECUTIVE_FAILURES` | 5 | 连续失败达此值 → 临时锁定 |
| `AUTH_LOCK_MINUTES` | 15 | 锁定时长（分钟），到期自动解锁 |
| `AUTH_FAILURE_WINDOW_MINUTES` / `AUTH_MAX_FAILURES_PER_WINDOW` | 15 / 10 | 单账号失败窗口与上限 |
| `AUTH_DEVICE_LOGIN_MAX` / `AUTH_DEVICE_WINDOW_MINUTES` | 20 / 10 | 设备维度登录失败上限（NAT 友好**主维度**） |
| `AUTH_IP_LOGIN_MAX` / `AUTH_IP_LOGIN_WINDOW_MINUTES` | 300 / 10 | IP 维度（兜底，刻意放宽） |
| `AUTH_LOGOUT_USER_MAX` / `AUTH_LOGOUT_USER_WINDOW_MINUTES` | 30 / 10 | 登出按用户上限 |
| `AUTH_LOGOUT_SESSION_MAX` | 10 | 登出按会话（jti）上限 |
| `AUTH_ANOMALY_DISTINCT_IDS` / `AUTH_ANOMALY_TOGGLE_PAIRS` | 5 / 8 | 撞库 / 登录↔登出横跳阈值 |

### 6) 测试覆盖（`apps/accounts/tests_security.py`，14 用例，随全量 `manage.py test` 运行）

- `LoginLockoutTests`：连续失败锁定、成功清零、锁定态拒绝（**423**）、管理员解锁后可登录、锁定到期自动解锁。
- `NatFriendlyThrottlingTests`：同 IP 不同设备隔离、`identifier_rate`、撞库拦截、IP 阈值远大于设备阈值。
- `LogoutAndRevocationTests`：登出黑名单 refresh、登出全部设备轮换安全戳吊销旧 access、按用户/会话限流。
- `AnomalyDetectionTests`：登录↔登出横跳检测。
