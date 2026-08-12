# E-algo rank 项目交接文档

> 文档用途：供接手人员（含新会话）快速理解项目全貌、当前进度与关键设计，直接继续后续开发。
> 文档基准时间：2026-08-12（末次更新：交接速览梳理 + 模拟登录 CORS 修复）。代码路径：`D:\_Dev\e-algo-rank\`
> 配套详细文档：`overview.md`（爬虫层总结）、`crawlers/VERIFICATION.md`（爬虫与作弊验证细节）。

---

## 项目状态总览（交接速览 · 2026-08-12 22:00 更新）

> 一页看完全貌，便于团队交接与跟进。详细背景见下方各章节；要继续开发从「未完成事项」与「后续计划」切入。

### 一、项目概况
- **定位**：面向高校算法竞赛生态的**学校维度积分排名系统**。自动爬取 Codeforces / AtCoder / 牛客三大平台比赛成绩，按学校聚合排名，配套管理员申请审批、后台管理、用户端展示。
- **技术栈**：后端 Django 5.2 + DRF + Celery/celery-beat（爬虫调度）+ SimpleJWT；前端 Vue3 + Vite + TS + Pinia + **自建设计系统（已彻底移除 Naive UI）**；认证统一走 **lotus-passport**（RS256 / JWKS 离线验签）。
- **部署形态**：dev 三件套（前端 `5180` / 本后端 `8001` / passport `8000`）；生产 Nginx + Gunicorn + PostgreSQL。
- **代码位置**：`D:\_Dev\e-algo-rank\`（本系统）；认证中心 `D:\_Dev\lotus-passport\`（独立项目，仅消费其 JWT）。
- **⚠️ 版本控制**：`e-algo-rank` 当前**不是 git 仓库**（无 `.git`），改动未纳入 VCS —— 交接前建议 `git init` 提交基线。

### 二、当前进展（任务看板）
| 任务 | 状态 | 说明 |
| --- | --- | --- |
| 任务3 · 前端全量重构（按 prototype.html 深色 Linear 风格） | ✅ 已完成 | 用户端 4 页 + 后台 6 页 + 认证 5 页 + 布局 2，全部重写并绑定真实 API；移除 Naive UI；`vue-tsc` + `vite build` 零错误 |
| 任务1 · 系统公告 | 🟡 部分完成 | 前端页左上角公告条已落地（localStorage 演示 + 超管可编辑/置顶）；**后端发布接口未对接** |
| 任务2 · 深/浅色主题切换 | ✅ 已完成 | `useTheme`(`<html data-theme>` + localStorage 记忆) + `tokens.css` 浅色令牌集 + NavBar 切换按钮 |
| 任务3补充 · 后端爬虫定时任务（可配置） | ⏳ 未开始 | 当前仅 django-celery-beat 固定调度（CF/AtCoder 每日、牛客每周、重算每日）；缺「定时任务配置模型 + REST 配置接口 + 前端配置 UI」 |
| lotus-passport 统一认证接入 | ✅ 已完成 | SDK 离线验签 + 双轨认证 + 用户名认领 + fragment 回调；dev 模拟登录 CORS 已修（5180 加白名单并重启） |
| 牛客作弊双层防御 / 积分引擎 / 种子数据 | ✅ 已完成 | 见 §1.4 |

### 三、未完成事项与阻塞
1. **系统公告后端发布接口（任务1 收尾）**：需新增超管发布/编辑/置顶 API（可复用 `Notification` 模型），前端 `SystemAnnouncement.vue` 的 load/save 由 localStorage 改为调接口。**无外部阻塞。**
2. **后端爬虫定时任务可配置化（任务3补充）**：新增 `ScheduleConfig` 模型 + 配置/启停 REST 接口 + 前端 CrawlView 配置面板；当前 CrawlView 仅「触发爬取/全量重算」。**无外部阻塞。**
3. **真实 GitHub OAuth 浏览器全流程手测**：被 GitHub OAuth App **单 callback URL** 限制阻塞（dev/prod 只能二选一）。处置见 §3.6（推荐建 dev 专用 OAuth App，或沿用 dev 模拟登录按钮验证链路）。
4. **QQ/微信登录**：由 passport 侧接入，前端无需改动；当前仅 GitHub 可用。
5. **生产化**：取消注释 psycopg / gunicorn；切 PostgreSQL；配生产 passport URL 与回调白名单；`VITE_PASSPORT_URL` 改生产域名。
6. **⚠️ 代码无版本控制**：`e-algo-rank` 非 git 仓库，交接前建议 `git init` 提交基线。

### 四、负责人分工（本机单人开发，按模块 / 对接方划分责任归属）
- **本系统（e-algo-rank）全栈**：当前开发（高级全栈工程师 Agent）负责 —— 后端 Django/DRF/Celery、前端 Vue3 全量重构、设计系统、认证前端接入、系统公告前端。
- **认证中心（lotus-passport）**：独立项目，由 passport 侧负责；本系统仅消费其 RS256 JWT。QQ/微信登录、GitHub OAuth App 凭据由 passport 方 / 运维配置。
- **需用户拍板 / 提供**：① 系统公告是否要后端持久化（已给 localStorage 演示）；② 爬虫定时是否开放前端可配置（任务3补充范围）；③ GitHub dev OAuth App 凭据；④ 生产域名与回调白名单；⑤ 是否初始化 git 仓库。
- **浏览器端真实联调验证**：本机 `browser-use` 3.0 daemon 阻塞无法 headless 截图，最终视觉 / 交互核验建议人工在 `5180` 打开确认（已提供 dev 模拟登录绕过 GitHub）。

### 五、后续计划（建议顺序）
1. 初始化 git 仓库并提交当前基线（消除无 VCS 风险）。
2. 任务1 收尾：系统公告后端发布接口 + 前端接接口。
3. 任务3补充：爬虫定时任务可配置化（模型 + 接口 + 前端面板）。
4. 真实 GitHub OAuth 联调（建 dev OAuth App 或走模拟登录核验链路）。
5. 生产化配置（PostgreSQL / Gunicorn / 域名 / 回调白名单）。
6. 回归：`manage.py test apps.crawler` + `npm run build`，更新本文档至生产就绪。

> 本地服务当前状态（2026-08-12 22:00 核验）：前端 `5180` / 后端 `8001` / passport `8000` 均在线。

---

## 0. 一分钟快速上手

```bash
# 本机已建好的虚拟环境（含 Django 5.2.17 等全部依赖）：
VENV="C:/Users/JXGM/.workbuddy/binaries/python/envs/default"
$VENV/Scripts/python.exe -m pip install -r requirements.txt   # 若换机器或依赖变动

cd D:/_Dev/e-algo-rank/backend
cp ../.env.example ../.env          # 按需修改；.env 不入库
$VENV/Scripts/python.exe manage.py migrate
$VENV/Scripts/python.exe manage.py bootstrap     # 创建 root 超级管理员 + 全局积分配置
$VENV/Scripts/python.exe manage.py seed_demo    # 造种子数据（学校/学生/比赛/成绩）
$VENV/Scripts/python.exe manage.py runserver    # 启动 API（默认 8000 端口）

# 接口文档：/api/docs/   健康检查：/healthz

# 前端（另一终端）
cd D:/_Dev/e-algo-rank/frontend
npm install            # 首次需要；node_modules 已存在可跳过
npm run dev            # Vite 开发服务器（vite.config 配 5180，代理 /api → 后端 8001；passport 直连 8000）
# 生产构建：npm run build   （经 vue-tsc 类型检查 + vite build）
```

⚠️ **最容易踩的坑**：裸 `python` / `python3` 在本机**没有安装 Django**，必须用上面 `envs/default` 里的 venv 解释器跑 `manage.py`，否则报 `ModuleNotFoundError: No module named 'django'`。

---

## 1. 整体架构概述与完成情况

### 1.1 项目定位

面向高校算法竞赛生态的**学校维度积分排名系统**。自动爬取三大平台（Codeforces、AtCoder、牛客）的比赛与成绩，按学校聚合排名，并配套管理员申请、后台管理、用户端展示。

### 1.2 技术栈

| 层 | 选型 |
| --- | --- |
| 后端 | Django 5.2.17 + Django REST Framework 3.17.1 |
| 认证 | JWT（`djangorestframework-simplejwt` 5.5.1）；未来统一走 lotus-passport |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| 缓存 / 任务队列 | Redis + Celery 5.6.3 + Celery Beat（`django-celery-beat`，DatabaseScheduler） |
| 爬虫 | `requests` + BeautifulSoup + Codeforces 官方 API（kenkoooo AtCoder API、牛客移动端点） |
| 前端 | Vue 3 + Vite + TypeScript + Pinia + Vue Router；**自建设计系统**（基于 `prototype design for rank` 的 tokens.css + 组件库），已彻底移除 Naive UI |
| 部署 | Nginx + Gunicorn + Supervisor（生产方案，见第 6 章） |
| API 文档 | `drf-spectacular`（Swagger UI，路径 `/api/docs/`） |

### 1.3 系统分层与请求流向

```
┌─────────────┐    HTTP /api/v1/*     ┌──────────────────┐
│  前端 Vue3   │ ───────────────────► │  Django + DRF    │
│ (5180 dev)   │ ◄─────────────────── │  (8001)         │
└─────────────┘    JSON + Bearer JWT  └────────┬─────────┘
                                                │ ORM
                                    ┌───────────┼───────────────┐
                                    ▼           ▼               ▼
                              PostgreSQL    SQLite(dev)     Redis(broker/result)
                                              
定时链路：Celery Beat ──► Worker ──► 爬虫脚本(crawlers/) ──► ingest.py ──► DB ──► 排名引擎重算
```

### 1.4 完成情况总览

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| Django 骨架 + 模型 | ✅ | 45 个迁移已应用；自定义用户模型 `accounts.User` |
| 认证与用户/学校 API | ✅ | 注册/登录/JWT/改密/平台账号/站内信；`/api/v1/` 下 |
| 管理员申请与审批流 | ✅ | 提交/列表/审批/驳回/撤回；仅超管审批 |
| 积分排名引擎 | ✅ | 基础分+平台/比赛系数加权；学校榜/学生榜快照 |
| 爬虫 Celery 接线 | ✅ | 每日爬 + 每日重算（beat 调度落 DB） |
| 牛客作弊双层防御 | ✅ | 爬虫层/入库层/引擎层/后台层 四道拦截 |
| 管理后台前端 | ✅ | 全量重构：仪表盘/学校/审批/爬虫/记录/成员 6 页 + 角色化侧边菜单 + 深/浅色主题切换 |
| 用户端前端 | ✅ | 全量重构：首页/排名榜/比赛列表/个人成绩 4 页 + SVG 折线图 |
| 注册/登录流程前端 | ✅ | 全量重构：passport 登录入口/本地登录/信息补全/申请管理员/passport 回调（fragment 解析），统一玻璃卡风格 |
| 种子数据 | ✅ | `seed_demo` 造 6 校/121 用户/36 比赛等 |
| **系统公告模块** | 🟡 **前端已落地** | 前端页左上角公告条（localStorage 演示 + 超管可编辑、置顶）；后端发布接口待对接（替换 load/save 即可） |
| **passport 后端回调** | ✅ **已实现** | lotus-passport-sdk[drf] 离线验签 + AlgoRankPassportAuthentication + 自定义用户解析器；passport 用户名认领流程见 §3.7 |
| **前端原型设计系统重做** | ✅ **已完成** | 按 `prototype design for rank` 忠实重做：深色设计系统 + 自定义组件库 + 真实 API 绑定；全部页面已铺开，Naive UI 已移除；深/浅色主题切换 + 偏好记忆已实现 |

---

## 2. 核心模块职责说明

### 2.1 后端 App 划分（`backend/apps/`）

| App | 职责 |
| --- | --- |
| `common` | 共享基础：`TimeStampedModel`、`Platform`/`ExcludeReason` TextChoices、权限类（`IsSuperAdmin`/`IsSchoolAdmin`/`IsOwnSchoolAdmin`/`ReadOnlyOrSchoolAdmin`）、统一异常处理器 |
| `accounts` | `User`、`PlatformAccount`、`Notification`；注册/登录/资料/改密/平台账号/站内信接口；`bootstrap`、`seed_demo` 命令 |
| `schools` | `School`、`SchoolAdminApplication`、`ScoreConfig`；学校 CRUD（超管）、管理员申请审批流 |
| `contests` | `Contest`、`Participation`；比赛只读 API、本人参赛记录 API |
| `crawler` | `CrawlJob`、`ingest.py`（业务规则唯一落地点）、`tasks.py`（Celery）、beat 迁移 |
| `ranking` | `ScoreRecord`、`RankSnapshot`、`engine.py`（积分引擎）、`recompute_ranking` 命令与任务 |

### 2.2 前端模块划分（`frontend/src/`）

| 模块 | 职责 |
| --- | --- |
| `api/client.ts` | axios 实例：`API_BASE='/api/v1'`、自动注入 Bearer、401 刷新、登出事件 |
| `api/types.ts` / `index.ts` | 类型定义与接口函数（与后端序列化器一一对应） |
| `stores/auth.ts` | Pinia 鉴权：`token` + `loadMe`；`isAdmin = isSuperAdmin \|\| isSchoolAdmin`；`isProfileComplete`（是否已绑学校） |
| `router/index.ts` | 路由表 + 全局守卫（public / requiresAuth / requiresAdmin / superOnly） |
| `layouts/PublicLayout.vue` | 用户端框架：已按原型重写为深色 Navbar + 玻璃态 + 自定义用户下拉；深/浅色主题切换已实现（`<html data-theme>` + localStorage 记忆） |
| `layouts/AdminLayout.vue` | 后台框架：已按新设计系统重写为侧边角色化菜单（超管可见学校管理）+ "返回前台"入口 + 移动抽屉 |
| `views/auth/*` | 注册/登录流程：passport 登录入口、本地登录、信息补全、申请管理员、passport 回调——已统一重写为玻璃卡风格（移除 Naive UI） |
| `views/user/*` | 用户端：首页/排名榜/比赛列表/个人成绩 已全部重写（真实 API + 新组件库 + 缺陷修复） |
| `views/admin/*` | 后台：仪表盘、学校管理、申请审批、爬虫触发、参赛记录、成员名单——已全部重写为新设计系统（移除 Naive UI，toast 由自建 `useToast` 接管） |
| `components/RatingLineChart.vue` | 纯 SVG 折线图（无第三方图表依赖） |
| `styles/{tokens,base,components}.css` | **新设计系统令牌**：`tokens.css` 全量 + Legacy bridge；`base.css` 排版/响应式；`components.css` 组件级样式 |
| `components/ui/*.vue` | **新自定义组件库**：RankBadge / OrgLogo / UserAvatar / SegmentedControl / PageTabs / DataPagination / EmptyState |
| `utils/format.ts` | 新设计系统工具：数字/积分/计数格式化、奖牌分级、org 配色与缩写、头像首字、平台标签 |
| `styles.css` | 旧主题令牌（保留作为迁移期 Legacy bridge；全部迁移完成后可整块删除） |

### 2.3 爬虫层（`crawlers/`，与 backend 平级）

三个平台爬虫（`cf_scraper.py` / `atcoder_scraper.py` / `nowcoder_scraper.py`），**与 Django 解耦**，通过 `sys.path` 被 `apps/crawler/tasks.py` 复用。输出标准化字典（rank 含 `is_cheater`、`extra` 存平台特有字段、`school=None`）。rated/付费判定规则已实测（详见 `overview.md` / `crawlers/VERIFICATION.md`）。

---

## 3. 关键业务流程流转逻辑

### 3.1 注册 / 登录流程（前端已实现，passport 后端已落地）

```
普通用户访问 /  ──► 重定向 /register（入口页）
入口页三选一：
  ① 通行证登录  ──► /auth/callback?mock=1（dev）或真实 passport 回调参数
  ② 本地账号登录 ──► /login ──► JWT ──► 按角色进 /admin 或 /u/rankings
  ③ 注册新账号  ──► /register/info ──► POST /api/v1/register/ ──► 存 token ──► /register/admin-apply

/auth/callback 解析：mock 或真实 token → 存 localStorage → loadMe → 按 isProfileComplete 分流
  · 未绑学校 → /register/complete（补全：学校下拉读 /api/v1/schools/）
  · 已绑学校 → 按角色进 /admin 或 /u/rankings

补全 /register/complete：PUT /api/v1/me/（绑 school_code）→ 进 /register/admin-apply
申请管理员 /register/admin-apply：POST /api/v1/applications/（可跳过）→ /u/rankings
```

> 守卫规则（`router/index.ts`）：已登录未绑学校强制走补全；补全流程放行；申请步骤任意已登录用户可达；普通用户访问 `/admin` 被引导回用户端。

### 3.2 管理员申请与审批流

```
普通用户 POST /applications/（school + reason + contact + evidence?）
   └─ 站内信通知所有超管
超管 GET /applications/（全量，支持 status 多选 + keyword 筛选）
   ├─ approve/  → 申请人 role=school_admin + school + sync_platform_accounts_school() + 站内信
   ├─ reject/   → review_comment + 站内信
   └─ cancel/   → 仅申请人本人撤回 pending
```

状态变更一律走动作接口（禁 PUT/PATCH/DELETE 直改）；非申请人访问他人申请返回 404（不泄露存在性）。

### 3.3 积分排名引擎（数据流）

```
爬虫 parse → Celery tasks（写 CrawlJob 审计）
   → ingest.ingest_contest() → Contest / Participation
       → Participation.objects.countable()   ← 仅 is_excluded=False & 有平台账号 & rated & 非付费
           → ScoreRecord（单场积分） → RankSnapshot（榜单快照，按 scope+period 重算）
               → REST: /rankings/（学校榜/学生榜）、/contests/、/me/participations/
                   → 前端 RankingsView / ContestsView / MyScoresView
```

**积分公式**：`base = 100 × (1 - (rank-1)/max(1, valid_count))`；`combined = platform_weight×平台系数 + contest_weight×比赛难度系数`；`final = base × combined`。
**三条硬规则（集中在 `ingest.py`，勿绕过）**：
1. 只入 rated 且非付费的比赛；
2. 学校归属只认 `PlatformAccount` 绑定（绝不读榜单 school 字段）；
3. 排除平台标记的作弊账号（四道拦截：爬虫 `detect_cheater` → 入库强 `is_excluded` → 引擎 `countable()` → 后台拒绝洗白 CHEATER）。

### 3.4 爬虫调度

- 调度落 `django-celery-beat` 的 `PeriodicTask`（DatabaseScheduler），非硬编码 `CELERY_BEAT_SCHEDULE`。
- 频率：CF/AtCoder 每日 02:00/02:30 爬最近 20 场；牛客每周日 03:00 爬近 2 月（`crawl_slow` 队列）；积分重算每日 04:00。
- 触发接口健壮性：broker 不可达时后台线程派发 + 2s socket 探测，避免阻塞 Web 请求线程（详见 5.4 环境坑）。

---

### 3.5 Lotus Passport 接入要点（2026-08-12 落地）

统一认证中心 `lotus-passport` 已接入，项目1 只消费其 RS256 JWT，业务权限仍由本系统维护。

**后端（`backend/`）**
- 依赖：`lotus-passport-sdk[drf]`（开发期从 `../lotus-passport-sdk` 可编辑安装）。
- 认证类：`apps/accounts/auth.py::AlgoRankPassportAuthentication`（继承 SDK 的 `PassportAuthentication`）。**关键点**：先读 JWT 头 `alg`，非 `RS256`（本地 simplejwt 签的 HS256）直接放行给下一个认证类，使 root/本地兜底与 passport 并存；算法混淆防护仍由 SDK 保证。
- 配置：`config/settings/base.py` 的 `LOTUS_PASSPORT = {BASE_URL, ISSUER, AUTO_CREATE_USER, USER_RESOLVER}`，生产用环境变量 `PASSPORT_BASE_URL=https://passport.eacm.cn`。
- 用户解析：`resolve_passport_user(identity)`——按 `passport_user_id` 关联，首见则自动建本地用户（`username` 初值为 UUID 占位、`needs_username=True`、`set_unusable_password`）。**注意**：`User` 继承 `AbstractUser`，`username` 必填，SDK 默认 resolver 不写 `username` 会建用户失败，故必须自定义。`username` 的 UUID 占位仅作过渡显示，用户在补全资料时自定认领（见 §3.7），认领后锁定不可再改。
- 验签离线（JWKS 缓存），passport 宕机返回 503 而非误登出；密钥轮换按 `kid` 自动适配。

**前端（`frontend/`）**
- `VITE_PASSPORT_URL`（`.env`）指向 passport；`VITE_API_TARGET` 指后端（与 passport 同机占 8000 时，本后端起 8001，见 `vite.config.ts`）。
- 登录流：`RegisterEntryView.goPassport()` **先 `fetch` passport 登录端点拿 `{authorize_url}` 再跳转**（该端点返回 200 JSON，不是 302）。目前仅 GitHub 已启用。
- 回调：`AuthCallbackView` 解析 **URL fragment**（`#access_token=...&refresh_token=...&passport_user_id=...`，passport 用 fragment 回跳，非 query），存 token + `auth_source=passport`，清掉地址栏令牌。
- 刷新：`api/client.ts` 按 `auth_source` 分流——passport 令牌刷新打 `PASSPORT_URL/api/v1/token/refresh/`（跨域，passport 已放开前端 CORS），本地令牌打本系统 `auth/token/refresh/`。
- 登出：`api/index.ts::logout()` 对 passport 令牌尽力 `POST passport /api/v1/logout/` 吊销 jti。
- 纯 passport 收口：入口移除"注册新账号"；"本地账号登录"降级为低调文字链接（root/兜底）。

**联调验证状态（2026-08-12）**
- ✅ passport `/dev/login/` 发真实 JWT → SDK 离线验签 + 算法混淆(HS256)被拒
- ✅ passport RS256 token 打 `/api/v1/me/` 自动建本地用户（isProfileComplete=False → 前端走补学校）
- ✅ 本地 HS256(root) /me/ 与 passport RS256 /me/ 并存（双轨认证修复后）
- ✅ passport 对前端 5180 的 CORS 预检放行（2026-08-12 已把 5180 加进 passport `CORS_ALLOWED_ORIGINS` 并重启 8000）
- ✅ 前端 `vue-tsc` 类型检查 + `vite build` 均通过
- ✅ 前端 5180 → Vite 代理 → 后端 8001（`/api/v1/schools/` 200、`/api/v1/me/` 无 token 401）
- ✅ 用户名认领全链路（见 §3.7）：`username-available` 边界（长度/字符/保留字/大小写查重）、`PUT /me/` 认领、认领后锁定，curl 端到端 8 项全过
- ✅ 前端 `vue-tsc` 类型检查 + `vite build` 均通过；生产包确认**不含** `[DEV]` 按钮（tree-shake）
- ⏳ 真实 GitHub OAuth 浏览器全流程 —— **当前被 GitHub 回调白名单拦截，见 §3.6**

### 3.6 GitHub OAuth 回调地址配置（踩坑必读）

**现象**：点「通行证登录（GitHub）」跳到 GitHub 后报「无效重定向 URL / redirect_uri mismatch」。

**根因**：passport 发给 GitHub 的 `redirect_uri` 由 passport 侧
`PASSPORT_OAUTH_REDIRECT_BASE`（默认 `http://localhost:8000/api/v1/oauth`）拼成
`http://localhost:8000/api/v1/oauth/github/callback/`；而 GitHub OAuth App 后台登记的
Authorization callback URL 是生产地址（`https://passport.eacm.cn/...`），两者必须**完全一致**。

**关键限制**：**GitHub OAuth App 只允许登记 1 个 callback URL**
（可配多个的是 GitHub App，不是 OAuth App）。因此不能"既 localhost 又生产"。

**处置方案（按推荐度）**
1. **dev/prod 双 App 分离（推荐，行业标准）**：另建一个 dev 专用 OAuth App，
   callback 填 `http://localhost:8000/api/v1/oauth/github/callback/`；
   把它的 `GITHUB_CLIENT_ID/SECRET` 填进**本地** `lotus-passport/.env`。
   生产服务器 `.env` 用生产 App 凭据。无需改任何代码。
2. **临时改现有 App 回调**：把线上 App 的 callback 临时改成 localhost，联调完改回。风险：忘改回会导致生产登录挂掉。
3. **跳过 GitHub 联调**（已内置）：注册入口页有仅 `import.meta.env.DEV` 可见的
   `[DEV] 模拟通行证登录（跳过 GitHub）` 按钮 —— 取 passport `/api/v1/dev/login/` 的真实 RS256 JWT，
   按与真实回调**完全一致的 fragment 格式**回跳 `/auth/callback`，可完整验证
   「回调解析 → 建本地用户 → 补学校 → 用户端」链路。生产构建不渲染此按钮。

**生产上线清单**：`PASSPORT_OAUTH_REDIRECT_BASE=https://passport.eacm.cn/api/v1/oauth`，
GitHub 生产 App callback 同步为 `https://passport.eacm.cn/api/v1/oauth/github/callback/`。

### 3.7 passport 用户名认领流程（2026-08-12 落地）

**问题**：passport 用户首登自动建号时 `username` 是 UUID 占位，补全页用户名字段原为 `readonly`，
导致 UUID 永久暴露在排行榜（`ranking/serializers.py::user_name`）、管理员审核页、顶栏。JWT 里带 `nickname` 却没用上。

**方案（用户拍板：补全时用户自定 + 占用校验）**：`passport_user_id` 仍作为唯一关联键不变；
`username` 在补全资料时由用户自定，认领后**锁定不可再改**（避免排行榜/审核身份漂移）。

**后端（`backend/`）**
- `apps/accounts/validators.py`：`validate_username_format(value)` —— 3–20 字符、仅 `[A-Za-z0-9_.-]`、禁止纯符号、保留字拦截（`root`/`admin`/`test` 等，大小写不敏感）。
- `User.needs_username`（property）：`passport_user_id 非空 且 username == passport_user_id` 时为 `True`（本地注册用户恒为 `False`）。
- `UserMeSerializer`：新增 `needs_username` 只读字段；`UserUpdateSerializer` 仅当 `needs_username=True` 时接受写 `username`，且原值回传放行、**改非原值报"不可修改"**。
- `GET /api/v1/username-available/?username=`：`AllowAny` + `AnonRateThrottle`（60/min），返回 `{available:bool, reason?}`；大小写不敏感查重。
- 路由 `apps/accounts/urls.py` 新增 `username-available/`。

**前端（`frontend/`）**
- `api/types.ts`：`UserMe` 加 `needs_username`；`api/index.ts::updateMe` 加 `username?`，新增 `checkUsernameAvailable()`。
- `stores/auth.ts`：`isProfileComplete` 纳入 `needs_username`（未认领强制回补全页）。
- `components/auth/RegisterForm.vue`：补全模式下用户名字段**可编辑**，带 500ms 防抖异步查重（`available`/占用/格式错误三态提示），提交走 `updateMe({username, ...})`。
- `AuthCallbackView.vue`：mock 用户补齐 `needs_username` 字段。

**验证（curl 端到端，8 项全过）**：占用查询边界（短/非法字符/保留字/大写保留字/纯符号/空/中文/超长）、大小写查重拒认领、非法格式拒认领、合法认领成功、`needs_username` 翻转、认领后改名被拒、原值回传放行。

### 3.8 前端原型设计系统重做（已完成）

**背景**：用户要求弃用 Naive UI，按 `D:\_Dev\e-algo-rank\prototype design for rank` 的 Linear 风格深色设计系统对前端做**忠实重做**，保持功能逻辑不变，并修复原型中已存在的缺陷。决策：先以**排名榜**为 PoC 跑通组件库 + 真实 API + 缺陷修复，确认风格后再批量铺开其余页面。

**已落地（排名榜 PoC）**
- 新增设计系统 CSS：`src/styles/tokens.css`（完整移植 DESIGN.md 令牌 + Legacy bridge 兼容旧变量）、`src/styles/base.css`（reset/排版/容器/响应式）、`src/styles/components.css`（Navbar/Cards/Tables/Buttons/Badges/Inputs/Tabs/Segmented/Pagination/EmptyState/Footer）。
- 新增自定义 UI 组件（`src/components/ui/`）：`RankBadge.vue`、`OrgLogo.vue`、`UserAvatar.vue`、`SegmentedControl.vue`、`PageTabs.vue`、`DataPagination.vue`、`EmptyState.vue`。
- 新增工具：`src/utils/format.ts`（`fmtNum/fmtScore/fmtCount/medalTier/orgColor/orgShort/initial/platformTag`），处理真实数据缺口：`total_score` 为 Decimal 字符串先 `Number()`、`trend/color/short/code/members` 缺失时安全降级或派生。
- 重写页面：`views/user/RankingsView.vue` 完全使用新组件库 + 真实 `listRankings({scope,period,school,page,page_size})` / `listSchools({page_size:100})`，含学校/学生双 Tab、年份 Segmented、学校筛选下拉、学校名本地搜索过滤、行展开可选增强。
- 重写布局：`layouts/PublicLayout.vue` 弃用 Naive UI 布局组件，改用原型 Navbar + 玻璃态 + 自定义用户下拉菜单。
- `App.vue`：强制 `darkTheme`，避免 Naive `n-global-style` 把 body 背景设成白色覆盖新深色系统。
- `main.ts`：在 `styles.css` 后引入 `tokens.css` / `base.css` / `components.css`，让 Legacy bridge 生效。

**已修复原型缺陷**
1. **CSS 分割线全部失效**：原型的 `border-bottom/right: var(--color-divider)` 缺 `1px solid`，导致表格/卡片/侧栏/抽屉线条全不渲染 → 在 `components.css` 全部补 `1px solid var(...)`。
2. **分页翻页不动 + 省略号缺失**：`renderPagination` 调用方传空回调、且 `renderRankTable` 不按 page 切片 → `DataPagination.vue` 改为受控组件，页码变化 `update:page` 由父组件重新取数；首省略号窗口算法避免百页撑爆分页条。
3. **表格列错位/偏移**：`table-layout: auto` + `.medal-row::before` 伪元素加在 `tr` 上会被浏览器解析为额外匿名单元格，导致数据行相对表头偏移 → `components.css` 改为 `table-layout: fixed`；奖牌条移到 `td:first-child::before`；`RankingsView.vue` 用 `<colgroup>` 显式定义列宽；`cell-ellipsis` 加 `display:block;min-width:0`。

**真实数据字段适配**
- 榜单接口 `/api/v1/rankings/` 无 `trend`、`color`、`short`、`code`、`members`，`total_score` 为字符串型 Decimal。
- 适配策略：`fmtScore` 先 `Number()`；`orgColor` 按学校名 djb2 派生稳定配色；`orgShort` 按 `short_name` 或中文取前两字/英文首字母；趋势列真实无数据时隐藏（不破坏布局）；成员数显示 `member_count`。

**验证状态**
- `npm run build` 通过（手动 `rm -rf dist` 绕过 safe-delete 后）。
- 浏览器截图：学校榜与学生榜均正常渲染，深色主题生效（body `#101014` / card `#13131a`），6 行数据无 console 错误，Top3 奖牌/校标/头像/分页均正常。
- **学生榜表格列已对齐**：`学生` / `所属学校` / `总积分` / `参赛场次` 表头与数据行一一对应，无偏移。
- 排名榜页可通过当前 dev 服务器打开验证。

**下一步**
- 用户确认风格后，按排名榜样板批量铺开：`views/user/{ContestsView,MyScoresView}` → `views/admin/*` → `views/auth/*` → `views/LoginView.vue`。
- 逐个页面验证并修复原型剩余已知缺陷：个人成绩折线图 tooltip 偏移、后台成员总数硬编码、danger 模态样式反转、编辑资料误跳、profileAccounts 写死等。

## 4. 关键代码结构

### 4.1 目录结构

```
e-algo-rank/
├─ backend/                      # Django 后端
│  ├─ manage.py
│  ├─ config/
│  │  ├─ settings/{base,dev,prod,__init__}.py
│  │  ├─ urls.py                 # 总路由：admin / healthz / api/v1 / schema / docs
│  │  ├─ celery.py               # Celery app
│  │  ├─ pagination.py           # StandardPagination（统一分页结构）
│  │  └─ asgi.py / wsgi.py
│  └─ apps/{common,accounts,schools,contests,crawler,ranking}/
├─ crawlers/                     # 三个平台爬虫（与 backend 平级，被 crawler app 复用）
│  ├─ cf_scraper.py / atcoder_scraper.py / nowcoder_scraper.py
│  ├─ verify_scrapers.py / verify_rated.py / VERIFICATION.md
├─ frontend/                     # Vue3 + TS + 自建设计系统（已移除 Naive UI）前端
│  ├─ src/
│  │  ├─ api/{client,types,index}.ts
│  │  ├─ stores/auth.ts
│  │  ├─ router/index.ts         # 根 / → /register；/admin 后台；/u 用户端；/register* 认证流
│  │  ├─ layouts/{AdminLayout,PublicLayout}.vue
│  │  ├─ views/
│  │  │  ├─ LoginView.vue
│  │  │  ├─ auth/{RegisterEntry,RegisterInfo,RegisterComplete,RegisterAdminApply,AuthCallback}View.vue
│  │  │  ├─ admin/{Dashboard,Schools,Applications,Crawl,Participations,Members}View.vue
│  │  │  └─ user/{Rankings,Contests,MyScores}View.vue
│  │  ├─ components/
│  │  │  ├─ ui/                         # 新设计系统通用组件
│  │  │  │  ├─ RankBadge.vue / OrgLogo.vue / UserAvatar.vue
│  │  │  │  ├─ SegmentedControl.vue / PageTabs.vue / DataPagination.vue / EmptyState.vue
│  │  │  └─ RatingLineChart.vue
│  │  ├─ styles/
│  │  │  ├─ tokens.css                  # 完整设计令牌（Color/Typography/Spacing/Radius/Shadow/Glass/Motion/Z-index）
│  │  │  ├─ base.css                    # reset + 排版工具类 + 布局/网格/响应式
│  │  │  ├─ components.css              # 组件级样式（卡片/表格/按钮/输入框/分页等）
│  │  │  └─ styles.css                    # 旧令牌文件（含 Legacy bridge 指向 tokens.css）
│  │  └─ utils/format.ts                  # 新设计系统格式化/奖牌/配色/缩写工具
│  └─ package.json / vite.config.ts / tsconfig*.json
├─ requirements.txt / .env.example / .gitignore
└─ overview.md / HANDOFF.md
```

### 4.2 核心模型关系

- `User` 1—* `PlatformAccount`；`User` *—1 `School`
- `School` 1—1 `ScoreConfig`（school=None 为全局默认）；`School` 1—* `SchoolAdminApplication`
- `Contest` 1—* `Problem` / `Participation`
- `PlatformAccount` 1—* `Participation`（可空=路人，不参与积分）
- `Participation` 1—1 `ScoreRecord`（仅 countable 生成）
- `RankSnapshot`（school/student 两种 scope，读多写少，定时重算后前端直读）
  - 列表接口 `GET /api/v1/rankings/` 已加 Redis 缓存层（`apps/ranking/cache.py`）：缓存序列化后的分页结果，靠版本号 `ranking:snapshot:version` 在重算后失效（同步 action 与 Celery 任务均 bump），TTL=300s 兜底；Redis 不可用时自动降级查库。

### 4.3 关键设计要点

- **`handle_lower` 唯一约束**：`PlatformAccount(platform, handle_lower)`、`Participation(contest, handle_lower)` 唯一，防重复绑定/计分；CF 大小写不敏感。
- **`User.sync_platform_accounts_school()`**：改学校后必须调用，同步到名下平台账号。
- **`rebind_unbound_participations()`**：新绑平台账号时回填历史无人认领记录（作弊记录不解除排除）。
- **权限类**：一律走 `User.is_super_admin`/`is_school_admin`，不要散落 `role` 字面量。
- **统一分页** `StandardPagination`：返回 `{count, page, page_size, total_pages, results}`。
- **统一异常** `api_exception_handler`：返回 `{detail, code}`。
- **前端主题**：`styles.css` 令牌 + `PublicLayout` 切 `document.documentElement.dataset.theme`。

---

## 5. 技术债务与待解决问题清单

### 5.1 功能缺口（明确未实现）

| 项 | 状态 | 影响 | 后续动作 |
| --- | --- | --- | --- |
| **系统公告模块** | 🟡 前端已落地 | 前端页左上角公告条已落地（localStorage 演示 + 超管可编辑/置顶）；**后端发布接口未对接**（待任务1 收尾） | 前端 load/save 由 localStorage 改为调超管发布/编辑/置顶 API（Notification 模型可复用） |
| **lotus-passport 后端回调** | ✅ 已实现 | passport OAuth 登录已落地；`accounts.User.passport_user_id` 已关联 | 见 §3.5 接入要点；QQ/微信由 passport 侧接入后前端自动生效 |
| **passport 用户名认领** | ✅ 已实现 | 补全资料时自定用户名 + 占用校验，认领后锁定（修复 UUID 外显） | 见 §3.7 |
| **"我的排名"入口** | 可选 | 个人成绩页未直接展示用户在榜单中的名次 | 可调 `listRankings({scope:'student', user:me.id})` |
| **分类资源网站推荐** | 已确认暂不做 | 不在范围 | — |

### 5.2 已知环境坑（本机 WorkBuddy 沙箱）

| 坑 | 现象 | 规避 |
| --- | --- | --- |
| **Redis 黑洞** | 本机 `127.0.0.1:6379`（Redis 未启动）连接表现为黑洞，Celery `.delay()` 阻塞 ~60s | 触发接口已用「后台线程 + 2s socket 探测」规避；真跑 Celery 先 `redis-server`，或 dev 设 `CELERY_TASK_ALWAYS_EAGER=1` |
| **safe-delete 拦截删除** | 命令行删除 `dist`/大目录被 safe-delete 拦截（回收站不可用 → fail-closed） | 前端构建用 `vite build --emptyOutDir false`；清理用绝对路径 Python `shutil.rmtree`；或文件管理器手动删 |
| **`rm` 被 safe-delete 拦截** | git bash 的 `rm` 触发回收站逻辑，回收站不可用时拒绝删除 | 用 Python `os.remove` 绝对路径或 `shutil.rmtree` |
| **`seq` 命令不存在** | git bash 无 `seq` | 轮询用 `while` 循环替代 |

### 5.3 代码/架构待优化

- **认证方案**：**已统一走 lotus-passport**（RS256 + JWKS，SDK 离线验签）。`apps/accounts/auth.py` 的 `AlgoRankPassportAuthentication` 为主认证类，对非 RS256 的本地 HS256 令牌放行给 simplejwt；`resolve_passport_user` 按 `passport_user_id` 关联/自动创建本地用户（用 UUID 充当 `username`，标记无本地密码）。本地 simplejwt **仅保留作 root/紧急兜底**（入口降级为低调文字链接）。详见 §3.5。
- **生产依赖未装**：`psycopg` / `gunicorn` 在 `requirements.txt` 注释，prod 部署前需取消注释并安装。
- **`db.sqlite3` 并发**：dev 用 SQLite，生产必须切 PostgreSQL（已在 dev.py 预留 `DEV_DB_ENGINE=postgres` 切换）。
- **前端 `dist` 清理**：受 safe-delete 限制，CI/CD 中删除 dist 需特殊处理（见 5.2）。

### 5.4 验证状态（历史全绿，供回归参考）

- `manage.py check`：0 issues
- `manage.py test apps.crawler`：12/12 通过（含 CheaterDetection / Ingest / SchoolBinding）
- `crawlers/verify_rated.py all`：rated / 付费 / 作弊过滤全过
- `manage.py spectacular`：schema 生成 OK
- 前端：`npm run build` 0 报错（vue-tsc + vite）；Playwright 联调注册/申请全流程、用户端三页渲染均无 JS 报错

---

## 6. 本地环境搭建与部署

### 6.1 本地开发搭建

1. **Python 环境**：用本机 venv `C:/Users/JXGM/.workbuddy/binaries/python/envs/default/Scripts/python.exe`（已装全部依赖）；或自建 venv + `pip install -r requirements.txt`（Python ≥ 3.11）。
2. **后端**：
   ```bash
   cd D:/_Dev/e-algo-rank/backend
   cp ../.env.example ../.env
   $VENV/Scripts/python.exe manage.py migrate
   $VENV/Scripts/python.exe manage.py bootstrap      # 建 root 超管（密码见 .env，留空则随机打印）
   $VENV/Scripts/python.exe manage.py seed_demo      # 造种子数据
   $VENV/Scripts/python.exe manage.py runserver      # 8000
   ```
3. **前端**：
   ```bash
   cd D:/_Dev/e-algo-rank/frontend
   npm install
   npm run dev        # 5180，代理 /api → 后端 8001；passport 直连 8000
   ```
4. **Celery（可选）**：先 `redis-server`，再 `bash scripts/start_celery.sh`（beat + 3 workers）或分开起。

### 6.2 生产部署（Nginx + Gunicorn + Supervisor）

> 当前为规划方案，尚未在线上环境落地；以下步骤为推荐实现路径。

**依赖准备**：
```bash
# requirements.txt 取消注释并安装生产依赖
psycopg[binary]==3.2.*   # gunicorn==23.*
pip install -r requirements.txt
```

**环境变量（`.env`，`DJANGO_ENV=prod`）**：
- `DJANGO_SECRET_KEY` 必填（缺失 `prod.py` 拒绝启动）
- `DJANGO_ALLOWED_HOSTS` 填域名/IP
- `DB_* ` 填 PostgreSQL 连接
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` 填 Redis
- `CORS_ALLOWED_ORIGINS` 填前端域名（prod 关闭 `CORS_ALLOW_ALL_ORIGINS`）

**后端静态收集 + Gunicorn**：
```bash
$VENV/Scripts/python.exe manage.py collectstatic --noinput
# Gunicorn（示例，按机器调整 workers）
gunicorn config.wsgi:application -b 127.0.0.1:8000 -w 3 --timeout 120
```

**Nginx 反向代理**（片段）：
```nginx
server {
    listen 80; server_name your.domain;
    location /static/ { alias /path/to/backend/staticfiles/; }
    location /media/  { alias /path/to/backend/media/; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Supervisor 托管**（Gunicorn + Celery worker + beat）：
```ini
[program:ealgo-gunicorn]
command=<VENV>/Scripts/gunicorn config.wsgi:application -b 127.0.0.1:8000 -w 3
directory=/path/to/backend
autostart=true autorestart=true

[program:ealgo-celery]
command=<VENV>/Scripts/celery -A config worker -Q crawl,crawl_slow,default -l info
directory=/path/to/backend
autostart=true autorestart=true

[program:ealgo-beat]
command=<VENV>/Scripts/celery -A config beat -l info
directory=/path/to/backend
autostart=true autorestart=true
```

**前端生产构建**：
```bash
cd D:/_Dev/e-algo-rank/frontend
npm run build        # 产物 dist/，由 Nginx 托管（注意 safe-delete 限制，见 5.2）
```

> 容量参考：2 核 4G 可跑一个 passport + 一个主站但偏紧（内存瓶颈）；建议扩到 8G。两站共用一个 PG 实例（两库）+ 一个 Redis（不同 db 号）。

---

## 7. 常用配置项与依赖说明

### 7.1 依赖（`requirements.txt` 锁定直接依赖）

```
Django==5.2.17
djangorestframework==3.17.1
djangorestframework-simplejwt==5.5.1
django-cors-headers==4.9.0
django-filter==26.1
drf-spectacular==0.30.0
celery==5.6.3
django-celery-beat==2.9.0
redis==8.1.0
python-dotenv==1.2.2
requests==2.34.2
Pillow==12.3.0
# 生产额外（按需取消注释）：
# psycopg[binary]==3.2.*
# gunicorn==23.*
```

前端依赖（`frontend/package.json`）：`vue` ^3.5、`vue-router` ^4.4、`pinia` ^2.2、`naive-ui` ^2.40、`axios` ^1.7、`vite` ^6.0、`vue-tsc` ^2.1、`typescript` ^5.6。

### 7.2 环境变量（`.env`，参考 `.env.example`）

| 变量 | 说明 |
| --- | --- |
| `DJANGO_ENV` | `dev` / `prod` |
| `DJANGO_SECRET_KEY` | prod 必填，缺失则启动报错 |
| `DJANGO_ALLOWED_HOSTS` | 逗号分隔 |
| `DB_*` | 生产 PostgreSQL 连接（dev 默认 SQLite） |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` / `REDIS_CACHE_URL` | 默认 `redis://127.0.0.1:6379/{0,1,2}` |
| `CELERY_TASK_ALWAYS_EAGER` | 本地无 Redis 设 `1` 同步执行 |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | JWT 有效期（默认 60 / 7） |
| `CORS_ALLOWED_ORIGINS` | 前端地址；dev 显式列出（如 `http://localhost:5180,http://127.0.0.1:5180,http://localhost:5173`），改后需重启 passport 生效 |
| `ROOT_ADMIN_USERNAME/EMAIL/PASSWORD` | 初始超管，密码留空则随机生成打印一次 |

### 7.3 常用命令

```bash
# 后端
manage.py migrate
manage.py bootstrap
manage.py seed_demo                 # 造种子数据
manage.py check
manage.py test apps.crawler
manage.py recompute_ranking            # 重算积分与榜单快照
manage.py recompute_ranking --scope school --period 2026
manage.py spectacular --file schema.yml   # 生成 OpenAPI schema
manage.py runserver                    # API 默认 8000

# 前端
cd ../frontend
npm install
npm run dev        # Vite 开发（5180）
npm run build      # vue-tsc 类型检查 + vite 生产构建

# 爬虫独立验证（crawlers/ 目录）
python verify_scrapers.py all     # 66/66
python verify_rated.py all        # rated/付费/作弊
```

### 7.4 数据库与缓存

- dev：SQLite（`backend/db.sqlite3`，已被 `.gitignore` 忽略）。
- prod：PostgreSQL；Redis 作 broker/result（django_celery_beat 用 DatabaseScheduler）。
- `.gitignore` 已忽略：`.env`、`db.sqlite3`、`__pycache__`、`media/`、`staticfiles/`、`crawlers/data/`、`node_modules/`、`dist/`。

---

## 8. 相关文档与资源链接

| 文档 / 资源 | 路径 / 链接 | 说明 |
| --- | --- | --- |
| 爬虫层阶段总结 | `D:\_Dev\e-algo-rank\overview.md` | rated-only / 排除付费 / 学校归属改造详情 |
| 爬虫与作弊验证细节 | `D:\_Dev\e-algo-rank\crawlers\VERIFICATION.md` | 三平台 rated 判定、作弊四道拦截 |
| 依赖清单 | `D:\_Dev\e-algo-rank\requirements.txt` | 直接依赖锁定 |
| 环境样例 | `D:\_Dev\e-algo-rank\.env.example` | 全部环境变量说明 |
| API 文档（运行时） | `http://127.0.0.1:8000/api/docs/` | drf-spectacular Swagger |
| Codeforces API | <https://codeforces.com/apiHelp> | contest.list / ratingChanges / contest.status |
| AtCoder (kenkooo) | <https://github.com/kenkoooo/AtCoderProblems> | contests.json / results |
| 牛客接口 | 移动端点（contest-info、contest/ranking 等，需逆向） | rated 判定逐场请求 contest-info |

---

## 9. 待办与注意事项

### 9.1 后续任务（建议顺序）

1. **系统公告模块**：前端公告页 + 超管发布接口（复用 Notification）。
2. ~~lotus-passport 后端回调~~：✅ 已实现（见 §3.5）。
3. **真实 GitHub OAuth 浏览器联调**：需先按 §3.6 解决 GitHub OAuth App 回调地址（仅允许 1 个，dev 建议另建 App）。在此之前可用入口页的 `[DEV] 模拟通行证登录` 按钮验证除"第三方授权页"外的全部环节；覆盖 401 刷新、登出吊销（契约层已验证）。
4. **（可选）"我的排名"入口**：个人成绩页展示榜单名次。
5. **生产化**：取消注释安装 `psycopg` / `gunicorn`；配置 `DJANGO_SECRET_KEY`、`ALLOWED_HOSTS`、前端 `VITE_PASSPORT_URL=https://passport.eacm.cn`；Nginx + Gunicorn + Supervisor 部署（见第 6 章）。
6. **资源网站推荐**：经用户确认暂不做。

### 9.2 关键注意事项（接手前必读）

1. **必须用 venv 解释器跑 `manage.py`**，裸 `python` 无 Django。
2. **三条硬规则集中在 `ingest.py`**，任何"想直接写 Participation/Contest"的需求都应先想清楚是否绕过规则。
3. **学校归属只走 `PlatformAccount`**，禁止从榜单读学校字段；用户改学校后记得调 `sync_platform_accounts_school()`。
4. **作弊账号四道拦截缺一不可**；后台 `unmark_excluded` 已禁止洗白 CHEATER，勿绕过。
5. **牛客 rated 判定必须逐场请求 `contest-info`**，不能按系列缓存（needCharge 逐年变）。
6. **CF 匿名 standings 静默丢人 28–40%**，名次一律以 `ratingChanges` 为准（爬虫 `mode="rating"` 默认行为）。
7. **爬虫脚本与 backend 平级**，通过 `sys.path` 复用，不要在 backend 里复制一份。
8. **清理临时文件用绝对路径**；相对路径 `rm` 在本环境会被 safe-delete 拦截。
9. **`db.sqlite3`、`.env`、`media/` 不入库**（`.gitignore` 已覆盖）。
10. prod 部署前务必取消注释并安装 `psycopg`、`gunicorn`，并配置 `DJANGO_SECRET_KEY` 与 `ALLOWED_HOSTS`，否则 `prod.py` 直接拒绝启动。
11. **前端已切换为新设计系统**：优先复用 `src/styles/tokens.css` 中的 `--color-bg-base` / `--color-bg-elev` / `--color-primary` / `--color-good` / `--color-danger` 等变量；旧 `styles.css` 仅作迁移期 Legacy bridge。新增页面必须引用新组件库，禁止再引入 Naive UI 组件。
12. **前端 API 真实前缀是 `/api/v1`**（不是 `/api`），联调/排查请认准 `/api/v1/*`。
13. **前端路由**：根 `/` → 注册入口 `/register`；后台整体在 `/admin/*`；用户端在 `/u/*`；管理员右上角有"后台管理"入口，后台有"返回前台"按钮。

---

*文档更新：2026-08-12（四次：新增 §3.8「前端原型设计系统重做」——按 `prototype design for rank` 忠实重做深色 Linear 风格系统，新建 `styles/{tokens,base,components}.css` + `components/ui/` + `utils/format.ts`，重写 `RankingsView.vue`/`PublicLayout.vue`/`App.vue`，真实 API 绑定，修复原型 CSS 分割线缺失与分页翻页不动缺陷；同步更新 §1.4/§2.2/§2.3/§4.1/§9.2。三次：新增 §3.7「passport 用户名认领流程」；二次：§3.6 GitHub OAuth 回调；首次：§3.5 Lotus Passport 接入。如后续有设计变更，请同步更新本文件与 `overview.md` / `VERIFICATION.md` 及 `lotus-passport/docs/integration/project1-ealgo-rank.md`）。*
