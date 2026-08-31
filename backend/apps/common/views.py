"""公开站点统计（首页数字看板）。

全部为公开榜单可推导的聚合数字（AllowAny）——首页统计不应依赖
管理端接口（/users/、/participations/ 为校管+权限，普通用户 403）。
"""
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contests.models import Contest, Participation
from apps.schools.models import School


class PublicStatsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        User = get_user_model()
        return Response(
            {
                "schools": School.objects.filter(is_active=True).count(),
                "contests": Contest.objects.count(),
                "users": User.objects.count(),
                "participations": Participation.objects.count(),
            }
        )
