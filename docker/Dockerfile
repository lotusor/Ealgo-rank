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
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 依赖缓存层（先拷 requirements 再拷代码）
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 复制整个仓库：backend 在 /app/backend，crawlers 在 /app/crawlers（爬虫任务依赖）
COPY . .

WORKDIR /app/backend

EXPOSE 8001

# 默认命令（docker-compose 对 worker/beat 覆盖 command）
# host 网络模式下绑定 127.0.0.1:8001，由 宝塔 nginx 反代
CMD ["gunicorn", "config.wsgi:application", \
     "-k", "gthread", "-w", "4", \
     "-b", "0.0.0.0:8001", "--timeout", "120", \
     "--env", "DJANGO_ENV=prod"]
