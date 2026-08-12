#!/usr/bin/env bash
# =====================================================================
# E-algo rank —— Celery 启动脚本（开发 / 生产通用）
#
# 前置：Redis 已启动（broker / result backend）
#   # 队列规划（见 config/settings/base.py -> CELERY_TASK_ROUTES）
#     crawl       : Codeforces / AtCoder 抓取（较快）
#     crawl_slow  : NowCoder 抓取（单场 1100 人约 65s，最慢）
#     default     : 积分重算 recompute_ranking_task 等
#
# 用法：
#   bash scripts/start_celery.sh          # 启动 beat + 三个 worker
#   bash scripts/start_celery.sh beat     # 仅 beat
#   bash scripts/start_celery.sh worker   # 仅 worker
# =====================================================================
set -euo pipefail

APP_MODULE="config"
BEAT_SCHEDULER="django_celery_beat.schedulers:DatabaseScheduler"

start_beat() {
  echo ">>> 启动 celery beat（读取 django-celery-beat 的 DB 调度）"
  celery -A "$APP_MODULE" beat -S "$BEAT_SCHEDULER" -l info
}

start_worker() {
  echo ">>> 启动 celery worker（按队列分别起，便于按负载调并发）"
  # crawl：常规并发
  celery -A "$APP_MODULE" worker -Q crawl -l info --concurrency 4 --max-tasks-per-child 50 &
  # crawl_slow：牛客最慢，低并发避免打满
  celery -A "$APP_MODULE" worker -Q crawl_slow -l info --concurrency 2 --max-tasks-per-child 20 &
  # default：积分重算等
  celery -A "$APP_MODULE" worker -Q default -l info --concurrency 2 --max-tasks-per-child 50 &
  wait
}

case "${1:-all}" in
  beat)   start_beat ;;
  worker) start_worker ;;
  all|*)  start_beat & start_worker ;;
esac
