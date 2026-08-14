# E-algo Rank 项目接手文档

> **本文件是本项目唯一的开发文档（single source of truth）。** 其他历史文档（`overview.md`、`BACKEND_HANDOFF.md`、`crawlers/VERIFICATION.md`）的内容已合并进本文，已删除，避免信息分叉。
> 文档基准时间：**2026-08-14**。代码路径：`D:\_Dev\e-algo-rank\`
> 配套设计原型（非开发文档，仅前端 UI 来源）：`prototype design for rank/{DESIGN|DELIVERY}.md` + `prototype.html`。

---

# 第一部分：项目进度

## 1.1 整体状态（2026-08-14）

面向**高校算法竞赛**的**学校维度积分排名系统**：自动爬取 Codeforces / AtCoder / 牛客三大平台成绩，按学校聚合排名，配套管理员申请审批、系统公告/站内信、后台管理与用户端展示。后端 Django + DRF + Celery，前端 Vue 3 + TS + Pinia + 自建设计系统（已移除 Naive UI），认证统一走 lotus-passport（RS256 离线验签）。

- ✅ **已是 git 仓库**（master 分支，提交历史完整），非早期文档所说的"无 VCS"。
- ✅ 核心功能（认证、爬虫调度、积分引擎、公告、站内信、权限体系、管理后台、用户端）**均已落地并验证**。
- ⏳ 生产化（PostgreSQL / Gunicorn / 真实 passport 域名）尚未落地。
- ⏳ 少量技术债务与可选增强见 §1.5。

## 1.2 已完成功能模块

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| Django 骨架 + 模型 | ✅ | 自定义用户模型 `accounts.User`；7 个 app（accounts/schools/contests/crawler/ranking/common/announcements） |
| 认证与用户 API | ✅ | 注册/登录/JWT/改密/平台账号/用户名认领（passport 首登 UUID 占位→补全页认领锁定） |
| Lotus Passport 接入 | ✅ | RS256 离线验签 + 双轨认证（HS256 本地兜底并存）；fragment 回调解析 |
| 管理员申请与审批流 | ✅ | 提交/列表/审批/驳回/撤回；仅超管审批；**申请校验**：原因必填、每月限一次、已是管理员禁止再申请 |
| 积分排名引擎 | ✅ | 基础分 + 平台/比赛系数加权；学校榜/学生榜快照 + Redis 缓存层 |
| 爬虫 Celery 接线 | ✅ | 每日爬 + 每日重算（beat 调度由迁移种子写入 DB） |
| **定时自动爬取配置** | ✅ | `CrawlConfig` 单例（超管设置启用开关/各平台抓取范围/触发小时）；`auto_crawl_task` 由 Beat 每日调度，`CrawlConfig` 变更经 signal 同步 beat crontab |
| 爬虫防重复爬取 | ✅ | 任务级：同平台+同参数去重窗口(1h)内已有进行中任务则不重复派发（Python 归一化比较）；比赛级：`Contest(platform, external_id)` 唯一约束 + `update_or_create` |
| 牛客作弊双层防御 | ✅ | 爬虫层标记 + 入库层强制排除（`is_excluded=cheater`） |
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

**当前无进行中开发任务。** 最近一轮（2026-08-14）修复了三项验收问题并已提交、全量验证通过（后端 **63 tests OK**，前端 typecheck 通过）：
- **#1 积分系数设置后台入口**：新增超管专属「积分系数设置」页（`/admin/score-config`，`superOnly`），读取/保存全局 `ScoreConfig` 单例。
- **#2 定时自动激活爬虫**：新增 `CrawlConfig` 单例（超管设置启用开关/各平台抓取范围/触发小时）；`auto_crawl_task` 由 Celery Beat 每日调度，读取 `CrawlConfig` 派发三平台；`CrawlConfig` 变更经 signal 同步 beat crontab；爬虫页「自动爬取设置」卡片可配置。
- **#3 爬虫防重复爬取**：任务级去重（同平台+同参数在 1h 窗口内已有进行中任务则不重复派发，Python 归一化比较，不依赖 JSON 列精确匹配）；比赛级已由 `Contest(platform, external_id)` 唯一约束 + `update_or_create` 保证幂等。

> 注意：本地运行需另起 **Celery worker + Beat**（`celery -A config worker -Q crawl,crawl_slow -l info` 与 `celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`）；Beat 调度条目由迁移 `0004_swap_beat_to_auto_crawl` 写入，本地已存在 `auto-crawl-daily`（每日 02:00）。

## 1.4 待办事项（建议顺序）

1. **生产化部署**：取消注释并安装 `psycopg` / `gunicorn`；配置 `DJANGO_SECRET_KEY`、`ALLOWED_HOSTS`、`VITE_PASSPORT_URL`；Nginx + Gunicorn + Supervisor（见 §2.6）。
2. **真实 GitHub OAuth 浏览器联调**：受 GitHub OAuth App 单 callback URL 限制（dev/prod 二选一）。建议另建 dev 专用 OAuth App，或沿用前端的 `[DEV] 模拟通行证登录` 按钮验证链路（见 §2.9）。
3. **（可选）"我的排名"入口**：个人成绩页展示用户在榜单中的名次（`listRankings({scope:'student', user:me.id})`）。
4. **（可选）AtCoder 学校别名归一化**：`Affiliation` 自填写法混乱，需别名表才能稳定按学校聚合（当前仅靠本地 handle↔学生绑定）。
5. **（已确认不做）分类资源网站推荐**：不在范围内。

## 1.5 已知技术债务 / 遗留问题

| 项 | 级别 | 说明 / 后续动作 |
| --- | --- | --- |
| **生产依赖未装** | 🟠 | `psycopg` / `gunicorn` 在 `requirements.txt` 中注释；prod 部署前需取消注释并安装 |
| **dev 用 SQLite** | 🟠 | 生产必须切 PostgreSQL（`dev.py` 已预留 `DEV_DB_ENGINE=postgres` 切换） |
| **`UserRole` 前后端枚举潜在不一致** | 🟡 | 后端 `UserRole.USER="user"`，旧文档曾报前端 `types.ts` 用 `'normal'`。当前前端主要依赖 `is_super_admin`/`is_school_admin` 布尔，**暂未爆**；新增用 `role` 字符串判断的逻辑前务必先对齐 |
| **`ScoreConfig` 系数无和校验** | 🟡 | `platform_weight + contest_weight` 未强制 =1，依赖人工/前端保证；Decimal 系数序列化后为字符串（前端已按 `string` 处理） |
| **`proposed_school_name` 未启用** | 🟡 | 申请只能绑"已存在学校"，无法申请系统里还没有的学校 |
| **`PlatformAccount.handle` 不可改** | 🟡 | 防止归属唯一性被破坏；改学校走 `sync_platform_accounts_school()` |
| **`UnorderedObjectListWarning`** | ⚪ | `ScoreConfig` 分页无 `ordering`，良性告警，不影响功能 |
| **Dead code：权限类** | ⚪ | `common/permissions.py` 中 `IsOwnSchoolAdmin` / `ReadOnlyOrSchoolAdmin` 已定义但未被任何视图引用；清理或接入前勿误用 |
| **本地无 Redis** | 🟠 | 见 §2.9 环境坑：Celery 触发接口已用后台线程 + socket 探测规避阻塞，但真跑 worker 需先 `redis-server` 或设 `CELERY_TASK_ALWAYS_EAGER=1` |

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
| `PASSPORT_BASE_URL` / `PASSPORT_ISSUER` | lotus-passport（默认 `http://127.0.0.1:8000` / `lotus-passport`） |
| `CORS_ALLOWED_ORIGINS` | 前端地址；改后需重启 passport 生效 |
| `ROOT_ADMIN_USERNAME/EMAIL/PASSWORD` | 初始超管，密码留空则随机生成打印一次 |
| `VITE_PASSPORT_URL` / `VITE_API_TARGET` | 前端：passport 地址 / 后端地址（同机时后端起 8001） |

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
manage.py test                 # 全量（当前 63 tests OK）
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
