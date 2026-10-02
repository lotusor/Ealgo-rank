# E-algo-rank 后端运行镜像
# 仅含后端（Django + Gunicorn + Celery）。前端为静态产物，由 宝塔 nginx 直接托管。
# 构建上下文 = 仓库根目录（需含 backend/ 与 crawlers/）。

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_ENV=prod

WORKDIR /app

# 系统依赖：libpq-dev 供 psycopg 编译（requirements 已启用 psycopg[binary]，仍装以防万一）
#
# 镜像源做成构建参数，默认走上游：
#   - 生产机在国内，直连 deb.debian.org / pypi.org 会被国际带宽拖到卡死，
#     部署时由 docker-compose.yml 传清华源（行为与改造前完全一致）；
#   - CI runner 在海外，反而连不上/很慢清华源。
# 写死国内源会让 CI 的镜像构建必挂 —— 这就是把环境耦合烧进 Dockerfile 的代价。
ARG APT_MIRROR=deb.debian.org
ARG PIP_INDEX_URL=https://pypi.org/simple

RUN if [ "$APT_MIRROR" != "deb.debian.org" ]; then \
        sed -i "s|deb.debian.org|$APT_MIRROR|g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

# 依赖缓存层（先拷 requirements 再拷代码）
# 注：依赖清单在仓库根 requirements.txt（backend/ 下无独立 requirements 文件）
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -i "$PIP_INDEX_URL" -r /tmp/requirements.txt

# 复制整个仓库：backend 在 /app/backend，crawlers 在 /app/crawlers（爬虫任务依赖）
COPY . .

# 统一认证中心 SDK：PyPI 未发布（演示项目），始终从 vendored 源码安装。
# 部署时仓库根需含 vendor/lotus-passport-sdk（由 .tmp_vendor 流程落地），不再回退 GitHub。
RUN echo ">>> vendor in build context:" && ls -la ./vendor/lotus-passport-sdk 2>/dev/null || (echo "MISSING ./vendor/lotus-passport-sdk — abort" && exit 1)
RUN pip install --no-cache-dir -i "$PIP_INDEX_URL" "./vendor/lotus-passport-sdk[drf]"

WORKDIR /app/backend

EXPOSE 8001

# 默认命令（docker-compose 对 worker/beat 覆盖 command）
# host 网络模式下只绑回环 127.0.0.1:8001，由 rank-nginx(:8003，同样只绑回环) 反代；
# 绑 0.0.0.0 会让直连 IP:8001 的请求绕过 TLS 终结、444 兜底 vhost 与响应头注入。
CMD ["gunicorn", "config.wsgi:application", \
     "-k", "gthread", "-w", "4", \
     "-b", "127.0.0.1:8001", "--timeout", "120", \
     "--env", "DJANGO_ENV=prod"]
