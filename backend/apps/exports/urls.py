"""导出接口路由。

统一挂在 `/api/v1/exports/`：
    GET    /exports/                 列表（校管仅自己 / 超管全站）
    POST   /exports/                 创建（同步 201 / 异步 202）
    GET    /exports/{id}/            状态轮询
    GET    /exports/{id}/download/   下载（必须带 Authorization）
    DELETE /exports/{id}/            撤销并删文件
"""
from rest_framework.routers import DefaultRouter

from apps.exports.views import ExportJobViewSet

router = DefaultRouter()
router.register("exports", ExportJobViewSet, basename="export")

urlpatterns = router.urls
