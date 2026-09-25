"""
爬虫相关视图：
- CrawlJob 列表 / 详情（只读，支持 platform / status 过滤）
- trigger 动作：手动触发一次爬取（建 CrawlJob 并派发 Celery 任务）
- CrawlConfig：自动爬取配置（超管可读写）
权限：仅超级管理员（IsSuperAdmin）。属系统底层信息，学校管理员不可访问或操作。
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsSuperAdmin
from apps.common.platforms import spec
from apps.crawler.models import CrawlConfig, CrawlJob
from apps.crawler.serializers import (
    CrawlConfigSerializer,
    CrawlJobSerializer,
    CrawlTriggerSerializer,
)
from apps.crawler.tasks import crawl_window_params, enqueue_crawl
from config.pagination import StandardPagination


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

        走统一的 enqueue_crawl 入口，自带重复防护（同一平台 + 相同参数在
        去重窗口内已有进行中任务时不再重复派发）。worker 未起 / broker
        不可达时，CrawlJob 状态会变为 failed，接口立即返回 201，不阻塞、不 500。
        """
        ser = CrawlTriggerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        platform = data["platform"]
        force = bool(data.get("force", False))

        # 参数形状由注册表声明（crawl_param + crawl_defaults），不再按平台名并列写
        # 分支：加一个平台若忘了在这里补 elif，接口会按「else」给它错参数。
        s = spec(platform)
        if s.crawl_param == "months_back":
            params = {}
            if data.get("months"):
                params["months"] = data["months"]
            elif data.get("months_back"):
                params["months_back"] = data["months_back"]
        else:
            params = crawl_window_params(s, data.get("count", 20))
        if force:
            params["force"] = True

        job = enqueue_crawl(platform, params, triggered_by=request.user)
        if job is None:
            # 去重命中：返回 200 并提示已由既有任务覆盖
            return Response(
                {"detail": "相同参数的爬取任务正在进行中，已去重跳过"},
                status=status.HTTP_200_OK,
            )
        return Response(CrawlJobSerializer(job).data,
                        status=status.HTTP_201_CREATED)


class CrawlConfigViewSet(viewsets.ModelViewSet):
    """
    自动爬取配置（CrawlConfig 单例），仅超级管理员可读写。
    - 列表/详情始终返回唯一配置（缺失则建默认）。
    - POST 改为 upsert（已存在则更新），不新建第二份。
    """

    serializer_class = CrawlConfigSerializer
    permission_classes = [IsSuperAdmin]
    queryset = CrawlConfig.objects.all()

    def get_object(self):
        return CrawlConfig.get_config()

    def list(self, request, *args, **kwargs):
        """单例语义：列表直接返回唯一配置对象，而非分页包裹。
        否则前端 GET /crawl-configs/ 拿到 {count, results} 而非字段对象，
        导致开关/数值在刷新后全部初始化。
        """
        cfg = CrawlConfig.get_config()
        serializer = self.get_serializer(cfg)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        cfg = CrawlConfig.get_config()
        serializer = self.get_serializer(cfg, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
