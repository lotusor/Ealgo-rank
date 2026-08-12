# E-algo Rank — 后端设计审查与前端开发交接文档

> 版本：基于代码现状（Django 5.2.17 / DRF 3.17.1），生成日期 2026-08-06
> 用途：前端工程师在新会话中独立开发/联调的唯一依据。所有接口、字段、枚举均来自源码核对，非推测。
> 配套运行文档见 `HANDOFF.md`（项目总览/部署）。

---

## 0. 审查结论速览（TL;DR）

| 维度 | 结论 |
|---|---|
| 数据模型 | ✅ 6 个 app、表/字段/关系/索引完整，迁移与模型**完全一致**（makemigrations --check = No changes） |
| API 覆盖 | ✅ 业务场景基本覆盖；⚠️ 通行证（lotus-passport）真实回调后端**缺失**，系统公告模块**未实现** |
| 认证/权限/校验/错误 | ✅ 统一 JWT + 权限类 + 统一异常体；⚠️ 前端 `UserRole` 类型与后端枚举值不一致（`user` vs `normal`） |
| 配置/部署 | ✅ 清晰；dev=SQLite+LocMemCache，prod=Postgres+Redis；Celery 定时重算**无默认 schedule 需自建** |
| 优先级缺口 | P0：passport 后端回调、系统公告。P1：role 枚举对齐、beat 定时任务、爬虫脚本依赖 |

---

## 1. 项目结构与技术栈

### 1.1 后端技术栈
- **Web 框架**：Django 5.2.17 + Django REST Framework 3.17.1
- **认证**：djangorestframework-simplejwt 5.5.1（JWT，Bearer）
- **数据库**：SQLite（dev，默认）/ PostgreSQL（prod，配置就绪）
- **缓存/队列**：Redis + Celery 5.6.3 + django-celery-beat 2.9.0（DatabaseScheduler）
- **其他**：django-cors-headers 4.9.0、django-filter 26.1、drf-spectacular 0.30.0、redis 8.1.0、Pillow 12.3.0
- **API 前缀**：**`/api/v1/`**（前端 `client.ts` 的 `API_BASE = '/api/v1'`）
- **交互式文档**：`/api/docs/`（Swagger，drf-spectacular）、`/api/schema/`（OpenAPI JSON）
- **健康检查**：`/healthz` → `{"status":"ok"}`（无认证）

### 1.2 应用结构（6 个 app）
```
backend/
├── config/            # 项目配置：settings(base/dev/prod)、urls、celery、pagination、wsgi/asgi
└── apps/
    ├── accounts/      # 用户、平台账号、站内信、注册/登录/改密
    ├── common/        # 公共：Platform/ExcludeReason 枚举、TimeStampedModel、权限类、统一异常
    ├── schools/       # 学校、管理员申请审批流、积分系数配置
    ├── contests/      # 比赛、参赛记录、个人参赛历史
    ├── crawler/       # 爬取任务记录与手动触发
    └── ranking/       # 积分记录、榜单快照、积分引擎、缓存层
```
> `common` 不含 views/urls，仅提供枚举、抽象基类、权限类（`IsSuperAdmin`/`IsSchoolAdmin`/`IsOwnSchoolAdmin`/`ReadOnlyOrSchoolAdmin`）与统一异常处理。

### 1.3 前端技术栈（供联调参考）
Vue 3 + Vite + TypeScript + Pinia + Vue Router + Naive UI；HTTP 用 axios（`src/api/client.ts`）。开发服务器默认 `:5173`，`/api` 代理到后端 `:8000`（见 `vite.config.ts`）。

---

## 2. 完整 API 清单

> 约定：
> - 所有接口前缀 `/api/v1`；响应分页结构统一为 `{count, page, page_size, total_pages, results}`（`StandardPagination`，`page_size` 默认 20，最大 200，可用 `?page_size=` 覆盖）。
> - 需认证的接口在请求头带 `Authorization: Bearer <access_token>`。
> - 权限标注：`公开`=无需登录；`登录`=IsAuthenticated；`校管`=IsSchoolAdmin（含超管）；`超管`=IsSuperAdmin。

### 2.1 认证（simplejwt 提供）
| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/auth/token/` | 公开 | 登录。body：`{username, password}` → 200 `{access, refresh}` |
| POST | `/auth/token/refresh/` | 公开 | 刷新。body：`{refresh}` → 200 `{access, refresh}`（**开启旋转，返回新 refresh**） |
| POST | `/auth/token/verify/` | 公开 | 校验。body：`{token}` → 200 / 401 |

### 2.2 账户 accounts
| 方法 | 路径 | 权限 | 请求 | 响应 |
|---|---|---|---|---|
| POST | `/register/` | 公开 | `{username, password, password2, email?, real_name?, student_no?, school_code?}` | 201 `{user: UserMe, access, refresh}` |
| GET | `/me/` | 登录 | — | 200 `UserMe` |
| PUT | `/me/` | 登录 | `{real_name?, student_no?, school_code?}`（partial） | 200 `UserMe` |
| POST | `/change-password/` | 登录 | `{old_password, new_password1, new_password2}` | 200 `{detail:"密码已修改"}` |
| GET | `/platform-accounts/` | 登录(本人) | — | 200 列表 `PlatformAccount`（仅本人） |
| POST | `/platform-accounts/` | 登录(本人) | `{platform, handle}` | 201 `PlatformAccount` |
| DELETE | `/platform-accounts/{id}/` | 登录(本人) | — | 204 |
| GET | `/notifications/` | 登录(本人) | `?unread=1` 仅未读 | 200 列表 `Notification` |
| GET | `/notifications/{id}/` | 登录(本人) | — | 200 `Notification` |
| POST | `/notifications/{id}/read/` | 登录(本人) | — | 200 `Notification`（标记已读） |
| POST | `/notifications/read_all/` | 登录(本人) | — | 200 `{detail:"已全部标记为已读"}` |
| GET | `/users/` | 校管 | `?school=&role=&keyword=` | 200 列表 `UserRoster`（超管全量，校管仅本校） |
| GET | `/users/{id}/` | 校管 | — | 200 `UserRoster` |

> 说明：`platform-accounts` 仅支持 增/删/查（不允许改 handle，避免破坏归属唯一性）；`users` 只读（用户角色变更走申请审批流，非直接 CRUD）。

### 2.3 学校 schools
| 方法 | 路径 | 权限 | 请求 | 响应 |
|---|---|---|---|---|
| GET | `/schools/` | 公开 | `?search=&ordering=` | 200 列表 `School`（**仅返回 is_active=True**） |
| GET | `/schools/{id}/` | 公开 | — | 200 `School` |
| POST | `/schools/` | 超管 | `School` 字段 | 201 `School` |
| PUT/PATCH | `/schools/{id}/` | 超管 | `School` 字段 | 200 `School` |
| DELETE | `/schools/{id}/` | 超管 | — | 204 |
| GET | `/applications/` | 登录 | `?status=(可多选)&keyword=` | 200 列表 `Application`（超管全量，普通用户仅本人） |
| POST | `/applications/` | 登录 | `{school, reason, contact, evidence?}`（multipart） | 201 `Application` |
| GET | `/applications/{id}/` | 登录 | — | 200 `Application`（本人或超管） |
| POST | `/applications/{id}/approve/` | 超管 | — | 200 `Application`（仅 pending 可审批，副作用：申请人角色→school_admin 并绑定学校、同步平台账号） |
| POST | `/applications/{id}/reject/` | 超管 | `{review_comment?}` | 200 `Application`（仅 pending） |
| POST | `/applications/{id}/cancel/` | 登录(本人) | — | 200 `Application`（仅本人+pending 可撤回） |
| GET | `/score-configs/` | 校管 | — | 200 列表 `ScoreConfig`（超管全量，校管仅本校） |
| POST | `/score-configs/` | 校管 | `ScoreConfig` 字段 | 201（校管强制绑定本校） |
| GET | `/score-configs/{id}/` | 校管 | — | 200 `ScoreConfig` |
| PUT/PATCH | `/score-configs/{id}/` | 校管 | `ScoreConfig` 字段 | 200 |
| DELETE | `/score-configs/{id}/` | 校管 | — | 204 |

### 2.4 比赛 / 参赛 contests
| 方法 | 路径 | 权限 | 请求 | 响应 |
|---|---|---|---|---|
| GET | `/contests/` | 公开 | `?platform=&is_rated=true\|false&name=&start_after=&start_before=` | 200 列表 `Contest` |
| GET | `/contests/{id}/` | 公开 | — | 200 `Contest` |
| GET | `/participations/` | 校管 | `?user=&contest=&platform=&is_excluded=&exclude_reason=` | 200 列表 `Participation`（校管仅本校） |
| GET | `/participations/{id}/` | 校管 | — | 200 `Participation` |
| POST | `/participations/{id}/exclude/` | 校管 | — | 200 `Participation`（标记排除，原因自动=manual） |
| POST | `/participations/{id}/restore/` | 校管 | — | 200 `Participation`（取消排除，原因自动清空） |
| GET | `/me/participations/` | 登录(本人) | `?platform=&is_excluded=` | 200 列表 `MyParticipation`（仅本人，用于个人成绩页/折线图） |

### 2.5 排名 ranking
| 方法 | 路径 | 权限 | 请求 | 响应 |
|---|---|---|---|---|
| GET | `/rankings/` | 公开 | `?scope=school\|student&period=all\|2026&school=&user=` | 200 列表 `RankSnapshot`（已加 Redis 缓存，重算后失效） |
| GET | `/rankings/{id}/` | 公开 | — | 200 `RankSnapshot` |
| POST | `/rankings/recompute/` | 超管 | — | 200 `{created, updated, deleted, snapshots:{...}}`（同步重算全量） |

### 2.6 爬虫 crawler
| 方法 | 路径 | 权限 | 请求 | 响应 |
|---|---|---|---|---|
| GET | `/crawl-jobs/` | 校管 | `?platform=&status=` | 200 列表 `CrawlJob` |
| GET | `/crawl-jobs/{id}/` | 校管 | — | 200 `CrawlJob` |
| POST | `/crawl-jobs/trigger/` | 校管 | `{platform, count?, months?, months_back?}` | 201 `CrawlJob`（建任务并后台派发 Celery；broker 不可达则标记 failed，接口不阻塞） |

> 触发参数说明：`platform` ∈ `codeforces|atcoder|nowcoder`；CF/AtCoder 用 `count`（默认 20）；牛客用 `months`（如 `["2026-07","2026-08"]`）或 `months_back`（最近 N 月，与 months 互斥，months 优先）。

---

## 3. 数据模型定义与枚举值

### 3.1 公共枚举（apps/common/models.py）
- **Platform**：`codeforces`(Codeforces) / `atcoder`(AtCoder) / `nowcoder`(牛客) — 值直接用于 DB 与 API 传参
- **ExcludeReason**：`""`(未排除) / `cheater`(平台标记作弊) / `post_contest`(赛后补交) / `unbound`(未绑定学生) / `manual`(人工剔除)
- **TimeStampedModel**：所有业务表继承，含 `created_at`、`updated_at`（自动）

### 3.2 accounts
- **UserRole**：`user`(普通用户) / `school_admin`(学校管理员) / `super_admin`(超级管理员)
- **User**（继承 AbstractUser）：`role`(索引)、`school`(FK→School, 可空)、`real_name`、`student_no`、`passport_user_id`(唯一索引，预留通行证关联)、`school_bound_at`；索引 `(school, role)`；属性 `is_super_admin`/`is_school_admin`
- **PlatformAccount**：`user`(FK)、`platform`、`handle`、`handle_lower`(索引)、`display_name`、`school`(冗余归属学校)、`verified`/`verified_at`；唯一约束 `(platform, handle_lower)`、`(user, platform)`
- **NotificationType**：`system` / `application_received` / `application_reviewed`
- **Notification**：`user`(FK)、`type`、`title`、`message`、`link`、`is_read`(索引)、`read_at`；索引 `(user, is_read)`

### 3.3 schools
- **School**：`name`(唯一)、`short_name`、`code`(Slug 唯一，URL 用)、`logo`(ImageField)、`description`、`is_active`(索引)
- **AdminApplicationStatus**：`pending` / `approved` / `rejected` / `cancelled`
- **SchoolAdminApplication**：`applicant`(FK)、`school`(FK)、`proposed_school_name`(当前未启用)、`reason`、`contact`、`evidence`(FileField)、`status`(索引)、`reviewer`、`review_comment`、`reviewed_at`；唯一约束 `(applicant, school)` 且 `status=pending`
- **ScoreConfig**：`school`(OneToOne, 可空=全局默认)、`cf_factor`/`atcoder_factor`/`nowcoder_factor`(Decimal)、`default_contest_factor`、`platform_weight`/`contest_weight`(两者之和应为 1)、`recent_contest_limit`(0=不限制)

### 3.4 contests
- **Contest**：`platform`(索引)、`external_id`(索引)、`name`、`url`、`start_time`(索引)、`end_time`、`duration_minutes`、`is_rated`(索引)、`is_paid`(索引)、`series`、`difficulty_factor`(Decimal)、`problem_count`、`participant_count`、`valid_participant_count`、`cheater_count`、`raw_meta`(JSON)；唯一 `(platform, external_id)`
- **Problem**：`contest`(FK)、`index`、`title`、`external_id`、`full_score`、`solved_count`、`raw`(JSON)；唯一 `(contest, index)`
- **Participation**：`contest`(FK)、`platform_account`(FK, 可空)、`handle`、`handle_lower`(索引)、`display_name`、`rank`(索引)、`solved_count`、`total_score`、`penalty_ms`、`rating_delta`/`old_rating`/`new_rating`、`is_excluded`(索引)、`exclude_reason`、`raw_display_name`、`score_detail`(JSON)、`extra`(JSON)；唯一 `(contest, handle_lower)`；管理器 `Participation.objects.countable()` = 积分引擎唯一入口（过滤 `is_excluded=False & platform_account 非空 & contest.rated & 非付费`）

### 3.5 crawler
- **CrawlJob.Status**：`pending` / `running` / `success` / `failed` / `partial`
- **CrawlJob**：`platform`(索引)、`status`(索引)、`triggered_by`(FK, 可空=定时)、`params`(JSON)、`celery_task_id`、`started_at`/`finished_at`、`contest_count`/`participation_count`/`cheater_count`、`error_message`、`log`

### 3.6 ranking
- **ScoreRecord**：`participation`(OneToOne)、`platform_account`(FK)、`school`(FK)、`platform`(索引)、`base_score`/`platform_factor`/`contest_factor`/`final_score`(索引)、`formula`、`contest_time`(索引)；索引 `(school, -final_score)`、`(platform_account, -contest_time)`
- **RankSnapshot.Scope**：`school`(学校榜) / `student`(个人榜)
- **RankSnapshot**：`scope`(索引)、`period`(索引, `all`/年份如 `2026`)、`school`(FK, 可空)、`user`(FK, 可空)、`rank`(索引)、`total_score`、`contest_count`、`member_count`、`detail`(JSON)、`computed_at`(索引)；索引 `(scope, period, rank)`

---

## 4. 认证流程与鉴权规则

### 4.1 登录态存储（前端）
- `localStorage.access_token`（JWT access，默认 60 分钟）、`localStorage.refresh_token`（默认 7 天）
- 每个请求经 axios 拦截器自动注入 `Authorization: Bearer <access>`
- **401 自动续期**：响应拦截器捕获 401 → 用 `refresh` 调 `/auth/token/refresh/` → 写入新 `access` → 重试原请求；刷新失败则清除 token 并派发 `auth:logout` 事件（前端监听后跳转登录）

### 4.2 后端鉴权
- DRF 默认认证 `JWTAuthentication`；默认权限 `IsAuthenticatedOrReadOnly`（只读公开、写需登录）
- 角色判断**一律走** `user.is_super_admin` / `user.is_school_admin`（属性），不要比较 `role` 字面量
- 权限类：`IsSuperAdmin`（危险操作）、`IsSchoolAdmin`（含超管）、`IsOwnSchoolAdmin`（对象级仅本校）、`ReadOnlyOrSchoolAdmin`（读开放写需校管）

### 4.3 ⚠️ 已知鉴权不一致（必须对齐）
1. **`UserRole` 枚举值前后端不一致**：后端 `UserRole.USER = "user"`，但前端 `types.ts` 定义 `UserRole = 'normal' | 'school_admin' | 'super_admin'`。真实后端返回的 `role` 是 `"user"`，与前端类型 `'normal'` 不符。
   - **影响**：凡前端用 `role === 'normal'` 判断普通用户处都会失效（当前 UI 主要依赖 `isProfileComplete`/`is_super_admin` 布尔，暂未爆，但是隐患）。
   - **处理建议**：二选一 —— 后端把 `UserRole.USER` 值改为 `"normal"`，或前端类型改为 `'user' | 'school_admin' | 'super_admin'`。**以本审查为准，建议后端改为 `"normal"` 以匹配前端语义**，或反之统一为 `"user"`。
2. **refresh 续期未更新 refresh_token**：simplejwt 开启 `ROTATE_REFRESH_TOKENS=True`，刷新接口返回新 `refresh`，但前端 `client.ts` 只存了 `access`（第 48 行），未更新 `refresh_token`。
   - 当前**不报错**的原因：`BLACKLIST_AFTER_ROTATION=False`（旧 refresh 未被拉黑，7 天内仍有效）。
   - **改进建议**：前端刷新成功时一并 `localStorage.setItem('refresh_token', data.refresh)`，以落实真正的单点刷新语义。

---

## 5. 统一错误码表

所有异常经 `apps/common/exceptions.api_exception_handler` 统一包装为：
```json
{ "detail": "人类可读信息", "code": "错误码", "errors": { /* 仅字段校验错误时 */ } }
```
> 前端应以 **HTTP 状态码为主、code 为辅**。code 为字符串标识，可作精确分支，但不要硬编码全部取值（新增 code 不应破坏前端）。

| HTTP | code（常见） | 含义 | 处理建议 |
|---|---|---|---|
| 400 | `validation_error` | 参数校验失败 | 读 `errors` 字段做表单内联提示 |
| 401 | `not_authenticated` / `authentication_failed` / `token_not_valid` | 未登录/凭证错/token 失效 | 触发刷新或跳转登录 |
| 403 | `permission_denied` | 无权限 | 提示无权限 |
| 404 | `not_found` | 资源不存在 | 跳转 404 或提示 |
| 405 | `method_not_allowed` | 方法不允许 | — |
| 429 | `throttle_error` | 限流（匿名 60/min，登录 600/min） | 提示稍后重试 |
| 500 | `server_error` | 未捕获异常 | 上报/重试，不暴露堆栈 |

> 校验错误示例：`{ "detail":"参数校验失败", "code":"validation_error", "errors": { "password2": ["两次密码不一致"] } }`

---

## 6. 本地运行与联调说明

### 6.1 后端启动（venv）
```bash
cd backend
# 用项目 venv（不要用裸 python）
<venv>/Scripts/python.exe manage.py migrate
<venv>/Scripts/python.exe manage.py bootstrap            # 创建 root 超管 + 全局默认积分配置
<venv>/Scripts/python.exe manage.py seed_demo           # 可选：构造 6 校/120 生/演示比赛并重算榜单
<venv>/Scripts/python.exe manage.py runserver 127.0.0.1:8000 --noreload
```
- 访问：`http://localhost:8000/`；API 根：`http://localhost:8000/api/v1/`；文档：`http://localhost:8000/api/docs/`
- Celery worker（重算/爬取异步）：`<venv>/Scripts/python.exe -m celery -A config worker -l info -Q crawl,crawl_slow,default`
- Celery beat（定时重算，见 §7 限制）：`<venv>/Scripts/python.exe -m celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`

### 6.2 前端启动
```bash
cd frontend
npm install
npm run dev        # 默认 :5173，/api 代理到 :8000
```
> 代理路径注意：**真实前缀是 `/api/v1`**（不是 `/api`）。前端 `baseURL='/api/v1'`，vite 代理 `/api` → `:8000`，组合后请求落在 `/api/v1/...`。联调误判 404 时先确认前缀。

### 6.3 CORS
- dev：`CORS_ALLOW_ALL_ORIGINS=True`（全开）
- prod：`CORS_ALLOWED_ORIGINS`（默认 `http://localhost:5173,http://127.0.0.1:5173`），`CORS_ALLOW_CREDENTIALS=True`
- 前端用 Bearer Header 而非 Cookie，无需 `withCredentials`

### 6.4 测试账号
| 角色 | 用户名 | 密码 | 说明 |
|---|---|---|---|
| 超级管理员 | `root` | 见 bootstrap 输出 / `.env ROOT_ADMIN_PASSWORD` | 由 `bootstrap` 创建；密码留空则随机生成并打印一次 |
| 普通学生（演示） | `{code}_stu01` 如 `thu_stu01` | `test1234` | `seed_demo` 生成，每校 20 人（thu/pku/zju/sjtu/fdu/uestc） |
> 注：root 密码请以你本地 `bootstrap` 实际输出或 `.env` 为准；演示学生统一 `test1234`。

### 6.5 时间格式
- `USE_TZ=True`，所有时间字段以 **ISO 8601 UTC**（如 `2026-08-05T12:00:00Z`）返回，前端按 UTC 解析并本地化显示。

---

## 7. 待办事项与已知限制（按优先级）

### 🔴 P0 — 阻断性 / 关键缺口
1. **通行证（lotus-passport）真实回调后端缺失**
   - 现状：前端 `RegisterEntryView`/`AuthCallbackView` 已按契约实现，并支持 `?mock=1` 本地验证；但后端**没有任何 passport 回调接口**（lotus-passport 是独立仓库，本次未接入）。
   - 影响：真实「微信/QQ/GitHub OAuth 登录」跳转后无后端签发 JWT 的落地接口，`/auth/callback` 在前端走 mock 分支。
   - 建议：在后端新增 passport 回调端点（校验 state、用 `passport_user_id` 关联/创建本地账号、签发 JWT），或暂明确「通行证登录为演示态」。
2. **系统公告模块未实现**
   - 现状：前端页 + 超管发布接口均无。审批结果靠 `Notification` 站内信（已实现），但「系统公告」独立功能缺失。
   - 建议：新增 `Announcement` 模型 + 超管发布接口 + 用户端公告列表。

### 🟠 P1 — 一致性 / 完备性
3. **`UserRole` 前后端枚举值不一致**（详见 §4.3-1）：后端 `"user"` vs 前端 `"normal"`。**必须对齐**，否则存在隐性 bug。
4. **Celery beat 定时重算无默认 schedule**
   - 现状：`CELERY_BEAT_SCHEDULER=DatabaseScheduler`，但代码里**没有预置周期性任务**，首次需通过 Django admin / 直接写 `django_celery_beat` 表配置（如每日重算 rankings）。
   - 建议：提供初始化 SQL 或管理命令写入默认 beat 周期任务。
5. **爬虫依赖外部脚本目录**
   - `CRAWLER_DIR = repo_root/crawlers`，Celery 任务直接调用其中的三个平台爬虫；若该目录/脚本缺失，`crawl-jobs/trigger/` 会建任务但执行失败（job 标记 failed）。
   - 建议：明确 crawler 脚本归属与初始化步骤，或在任务内做存在性校验并给出清晰错误。
6. **`RankSnapshot` 重算仅超管可触发**：普通用户/校管无法手动触发；生产依赖 beat 定时。若 beat 未配，榜单只有在超管手动点「重算」后才更新。

### 🟡 P2 — 改进项
7. **`refresh` 未回写 refresh_token**（详见 §4.3-2）：建议前端刷新时同步更新 `refresh_token`。
8. **`proposed_school_name` 字段未启用**：模型有此字段，但申请只允许绑「已存在学校」，无法申请「系统里还没有的学校」。
9. **`ScoreConfig` 系数无和校验**：`platform_weight + contest_weight` 未强制=1，依赖前端/人工保证；Decimal 系数序列化后为**字符串**（前端 `types.ts` 已按 `string` 处理，保持一致即可）。
10. **`/me/participations/` 与 `/me/` 路径易混**：前者是本人参赛记录（contests app），后者是当前用户信息（accounts app），均位于 `/api/v1/me/...`，前端调用时注意区分。
11. **`school.logo` 为 ImageField**：返回相对 URL，dev 仅在 `DEBUG=True` 时由 `static()` 提供；prod 需 Nginx 托管 `MEDIA_ROOT`。前端展示需拼接 base。
12. **错误码非集中常量**：code 散落在异常处理器与 DRF 默认中，前端应把 code 当不透明标识 + 以 HTTP 状态为主分支。
13. **限流**：匿名 60/min、登录 600/min，前端应处理 429（提示重试）。

### ✅ 已确认完整/正确项
- 迁移与模型**完全一致**（`makemigrations --check` = No changes；accounts 3 / schools 1 / contests 1 / crawler 2 / ranking 1 个迁移）。
- 积分引擎三道硬规则（`countable` 唯一入口、排除原因与标记同进同出、平台账号唯一约束）均已落地。
- 排名快照 Redis 缓存层已加（版本号失效 + 降级），详见 `apps/ranking/cache.py`。
- 管理命令齐全：`bootstrap`、`recompute_ranking`、`seed_demo`。

---

## 8. 前端开发 Checklist（开箱即用）
- [ ] 所有请求走 `client.ts`（已注入 Bearer、已处理 401 续期）
- [ ] 分页统一读 `count/page/page_size/total_pages/results`
- [ ] 错误统一读 `{detail, code, errors?}`，以 HTTP 状态分支
- [ ] 时间按 UTC 解析
- [ ] **对齐 `UserRole` 枚举**（§4.3-1）后再使用 `role` 做判断
- [ ] 申请管理员用 `multipart/form-data`（evidence 为文件）
- [ ] 榜单用 `?scope=&period=&school=&user=` 过滤；重算后缓存自动失效
- [ ] 学校列表只返回启用中的（`is_active=True`）
- [ ] 超管后台入口在 `/admin/*`（前端路由已配置），`recompute` 仅超管可用
