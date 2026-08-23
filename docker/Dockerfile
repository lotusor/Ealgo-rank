# E-algo-rank 后端运行镜像
# 仅含后端（Django + Gunicorn + Celery）。前端为静态产物，由 宝塔 nginx 直接托管。
# 构建上下文 = 仓库根目录（需含 backend/ 与 crawlers/）。

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_ENV=prod

WORKDIR /app

# 系统依赖：libpq-dev 供 psycopg 编译（requirements 已启用 psycopg[binary]，仍装以防万一）
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

# 依赖缓存层（先拷 requirements 再拷代码）
# 注：依赖清单在仓库根 requirements.txt（backend/ 下无独立 requirements 文件）
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 复制整个仓库：backend 在 /app/backend，crawlers 在 /app/crawlers（爬虫任务依赖）
COPY . .

# 统一认证中心 SDK：PyPI 未发布（演示项目），始终从 vendored 源码安装。
# 部署时仓库根需含 vendor/lotus-passport-sdk（由 .tmp_vendor 流程落地），不再回退 GitHub。
RUN echo ">>> vendor in build context:" && ls -la ./vendor/lotus-passport-sdk 2>/dev/null || (echo "MISSING ./vendor/lotus-passport-sdk — abort" && exit 1)
RUN pip install --no-cache-dir "./vendor/lotus-passport-sdk[drf]"

WORKDIR /app/backend

EXPOSE 8001

# 默认命令（docker-compose 对 worker/beat 覆盖 command）
# host 网络模式下绑定 127.0.0.1:8001，由 宝塔 nginx 反代
CMD ["gunicorn", "config.wsgi:application", \
     "-k", "gthread", "-w", "4", \
     "-b", "0.0.0.0:8001", "--timeout", "120", \
     "--env", "DJANGO_ENV=prod"]
