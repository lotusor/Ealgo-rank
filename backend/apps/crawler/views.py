"""
爬虫相关视图：
- CrawlJob 列表 / 详情（只读，支持 platform / status 过滤）
- trigger 动作：手动触发一次爬取（建 CrawlJob 并派发 Celery 任务）
权限：仅超级管理员（IsSuperAdmin）。属系统底层信息，学校管理员不可访问或操作。
"""
import socket
import threading
from urllib.parse import urlparse

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.models import Platform
from apps.common.permissions import IsSuperAdmin
from apps.crawler.models import CrawlJob
from apps.crawler.serializers import CrawlJobSerializer, CrawlTriggerSerializer
from apps.crawler.tasks import (
    crawl_atcoder,
    crawl_codeforces,
    crawl_nowcoder,
)
from config.pagination import StandardPagination

TASK_MAP = {
    Platform.CODEFORCES: crawl_codeforces,
    Platform.ATCODER: crawl_atcoder,
    Platform.NOWCODER: crawl_nowcoder,
}


def _broker_reachable():
    """快速探测 broker（Redis）是否可达。

    本沙箱里连到未监听的本地端口会“黑洞”而非立即 refused，导致 Celery
    的 .delay() 阻塞数十秒；这里用 2s 超时原生 socket 探测，快速判定。
    """
    raw = getattr(settings, "CELERY_BROKER_URL", "") or "redis://127.0.0.1:6379/0"
    parsed = urlparse(raw)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def _dispatch_crawl(task, job_id, params):
    """后台派发 Celery 任务。

    broker 不可达（Redis 未启动等）时：先快速探测，不可达则直接标记 failed，
    避免阻塞；可达则 dispatch（生产环境 Redis 在线时为瞬时操作）。
    """
    if not _broker_reachable():
        CrawlJob.objects.filter(pk=job_id).update(
            status=CrawlJob.Status.FAILED,
            error_message="任务派发失败：无法连接消息队列，请确认 Redis / Celery worker 已启动",
        )
        return
    try:
        task.delay(job_id=job_id, **params)
    except Exception as exc:  # noqa: BLE001 - 任何派发异常都标记失败
        CrawlJob.objects.filter(pk=job_id).update(
            status=CrawlJob.Status.FAILED,
            error_message=f"任务派发失败：{exc}",
        )


class CrawlJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CrawlJobSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardPagination
    queryset = CrawlJob.objects.all()
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = CrawlJob.objects.all()
        platform = self.request.query_params.get("platform")
        status_ = self.request.query_params.get("status")
        if platform:
            qs = qs.filter(platform=platform)
        if status_:
            qs = qs.filter(status=status_)
        return qs

    @action(detail=False, methods=["post"],
            permission_classes=[IsSuperAdmin])
    def trigger(self, request):
        """手动触发一次爬取：建 CrawlJob 并（后台）派发 Celery 任务。

        worker 未起 / broker 不可达时，任务在后台线程尝试派发；若失败
        CrawlJob 状态会变为 failed，接口本身立即返回 201，不阻塞、不 500。
        """
        ser = CrawlTriggerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        platform = data["platform"]
        task = TASK_MAP[platform]

        if platform == Platform.CODEFORCES:
            params = {"count": data.get("count", 20), "mode": "rating"}
        elif platform == Platform.ATCODER:
            params = {"count": data.get("count", 20)}
        else:  # NOWCODER
            params = {}
            if data.get("months"):
                params["months"] = data["months"]
            elif data.get("months_back"):
                params["months_back"] = data["months_back"]

        job = CrawlJob.objects.create(
            platform=platform, triggered_by=request.user, params=params)
        # 后台派发，避免 broker 不可达时阻塞请求线程
        threading.Thread(
            target=_dispatch_crawl, args=(task, job.pk, params),
            daemon=True, name=f"dispatch-crawl-{job.pk}",
        ).start()
        return Response(CrawlJobSerializer(job).data,
                        status=status.HTTP_201_CREATED)
