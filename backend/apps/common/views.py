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
        from apps.crawler.ingest import (CALENDAR_RATED_SOURCE,
                                         PROFILE_RATED_SOURCE)

        User = get_user_model()
        # 锚点赛次（不计分场次展示行）与日历排期行都不是「已收录的比赛」，
        # 计进来会让首页数字看板虚高（§0.25 已因锚点漂移过一次）。
        contests = Contest.objects.exclude(
            rated_source__in=[PROFILE_RATED_SOURCE, CALENDAR_RATED_SOURCE])
        return Response(
            {
                "schools": School.objects.filter(is_active=True).count(),
                "contests": contests.count(),
                "users": User.objects.count(),
                "participations": Participation.objects.count(),
            }
        )
