"""
announcements 视图：
- 用户端列表（公开，无需登录）：只返回启用中的公告，按 pinned→updated_at 排序
- 超管 CRUD：新建/编辑/删除/启停，可管理全部（含已停用）公告
"""
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.announcements.models import Announcement
from apps.announcements.serializers import AnnouncementSerializer
from apps.common.permissions import IsSuperAdmin
from config.pagination import StandardPagination


class AnnouncementPublicView(APIView):
    """用户端公告列表：公开只读，只给启用中的。前端顶栏轮播用。"""

    permission_classes = [AllowAny]

    def get(self, request):
        qs = Announcement.objects.filter(is_active=True)
        serializer = AnnouncementSerializer(
            qs, many=True, context={"request": request})
        return Response(serializer.data)


class AnnouncementViewSet(viewsets.ModelViewSet):
    """超管专用：公告的增删改查与启停。普通用户/未登录走 public 接口。"""

    serializer_class = AnnouncementSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Announcement.objects.all()
        if self.request.query_params.get("active") == "1":
            qs = qs.filter(is_active=True)
        if self.request.query_params.get("level"):
            qs = qs.filter(level=self.request.query_params["level"])
        return qs
