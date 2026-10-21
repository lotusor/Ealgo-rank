# E-algo Rank

[![CI](https://github.com/lotusor/Ealgo-rank/actions/workflows/ci.yml/badge.svg)](https://github.com/lotusor/Ealgo-rank/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

面向高校学生的算法竞赛积分排名平台：采集 Codeforces、AtCoder、牛客、洛谷等平台的比赛与成绩，按统一口径计算表现分、赛季积分与学校榜，并提供竞赛日历、个人成绩中心和学校管理后台。

## 功能

- 多平台成绩采集与参赛记录入库
- 统一表现分 / 赛季积分 / 学校榜与学生榜
- 竞赛日历与排期同步，支持 rated / 不计分场次标注
- 学生、学校管理员、超级管理员三级权限
- 统一登录：通过 Lotus Passport 完成 OAuth / JWT 认证
- 管理后台：学校、成员、参赛记录、爬虫任务、公告与审批
- 爬虫缓存、断点补抓、调度与失败重试

## 架构

```text
Vue 3 + Vite SPA
      │  /api/v1 (same-origin)
      ▼
  Nginx / 静态产物
      │
      ▼
Django + DRF ──── PostgreSQL
      │
      ├────────── Redis（缓存 / Celery broker）
      │
      ├────────── Celery worker + beat
      │             │
      │             └── crawlers（CF / AtCoder / 牛客 / 洛谷 / clist）
      │
      └────────── Lotus Passport（RS256 JWT / JWKS）
```

## 仓库结构

| 路径 | 内容 |
|---|---|
| `backend/` | Django 项目：账号、学校、比赛、排名、爬虫、公告 |
| `crawlers/` | 各平台抓取器、缓存与联网校验脚本 |
| `frontend/` | Vue 3 + Vite 前端 |
| `deploy/` | 反向代理与部署模板（生产专有配置请放私有 ops 仓库） |
| `docker/` | 后端镜像 |
| `docker-compose.yml` | 本地 / 演示编排 |
| `.github/` | CI、公开仓库门禁、Issue / PR 模板 |

## 快速开始

### 后端

```bash
git clone https://github.com/lotusor/Ealgo-rank.git
cd Ealgo-rank

python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements.txt

cp .env.example .env
# 按需修改 DJANGO_SECRET_KEY、数据库 / Redis 连接；.env 已被 gitignore

cd backend
python manage.py migrate
python manage.py bootstrap       # 创建 root 超级管理员，密码随机生成并只打印一次
python manage.py runserver 127.0.0.1:8001
```

### 前端

```bash
cd frontend
npm ci
VITE_API_TARGET=http://localhost:8001 npm run dev
```

Vite 默认在 `5173` 启动，并把 `/api` 代理到 `VITE_API_TARGET`。生产构建：

```bash
npm run build
```

构建产物在 `frontend/dist/`。

### 测试

```bash
cd backend
python manage.py test
python manage.py makemigrations --check --dry-run
```

前端：

```bash
cd frontend
npm run typecheck
npm run build
```

## 环境变量

仓库只提交 `*.example` 模板。生产值通过环境变量或密钥管理注入，禁止提交真实 `.env`、数据库密码、OAuth secret、SMTP 授权码。

常用变量见 [`.env.example`](.env.example) 与 [`.env.prod.example`](.env.prod.example)：

| 变量 | 说明 |
|---|---|
| `DJANGO_ENV` | `dev` / `prod` |
| `DJANGO_SECRET_KEY` | 生产必须使用强随机值 |
| `DJANGO_ALLOWED_HOSTS` | 允许的 Host 列表 |
| `DB_*` | PostgreSQL 连接 |
| `CELERY_*` / `REDIS_CACHE_URL` | Redis 与 Celery |
| `PASSPORT_BASE_URL` / `PASSPORT_AUDIENCE` | Lotus Passport 接入 |
| `CLIST_USERNAME` / `CLIST_API_KEY` | 竞赛日历排期源 |

开发环境默认使用 SQLite；不启动 Redis 时可设置 `CELERY_TASK_ALWAYS_EAGER=1`。

## 开发约定

- 提交前运行公开仓库门禁与后端测试；前端改动额外运行 `vue-tsc` 与 `vite build`。
- 不要提交真实主机、面板、数据库、证书或运维交接文档；公开仓库只保留产品代码与脱敏模板。
- 演示数据命令 `seed_demo` 与测试账号命令 `create_test_users` 仅在 `DEBUG=True` 下可用，且必须显式提供密码。
- 新增平台请遵循后端 `apps/common/platforms.py` 与前端 `frontend/src/platforms/meta.ts` 的注册表约定。

## 安全

- 漏洞请通过 GitHub Security Advisories 私下报告，不要开公开 Issue；见 [SECURITY.md](SECURITY.md)。
- 公开仓库门禁会拦截密钥、真实 `.env`、内部文档、构建缓存与公网 IP。
- 如果敏感内容曾经进入 git 历史，删除文件并不能消除历史；请按 [CONTRIBUTING.md](CONTRIBUTING.md) 的流程先轮换凭据、再清理历史。

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)
