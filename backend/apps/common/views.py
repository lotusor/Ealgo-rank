"""公开站点统计（首页数字看板）。

全部为公开榜单可推导的聚合数字（AllowAny）——首页统计不应依赖
管理端接口（/users/、/participations/ 为校管+权限，普通用户 403）。
"""
from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import PlatformAccount
from apps.common.platforms import PLATFORM_SPECS
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
        # 逐平台给真实计数：首页「支持的平台」卡片原先写死 712/2103 这类假数字，
        # 加一个平台就得再编一组。按注册表出数后，新平台自动带着 0 出现，
        # 由前端决定怎么讲「赛程已接入、成绩还没有」这个状态。
        accounts = {row["platform"]: row["n"] for row in
                    PlatformAccount.objects.values("platform").annotate(
                        n=Count("id"))}
        per_platform = [{
            "key": s.value,
            "label": s.label,
            "contests": contests.filter(platform=s.value).count(),
            "accounts": accounts.get(s.value, 0),
            "scoring": s.scoring,
        } for s in PLATFORM_SPECS]
        return Response(
            {
                "schools": School.objects.filter(is_active=True).count(),
                "contests": contests.count(),
                "users": User.objects.count(),
                "participations": Participation.objects.count(),
                "platforms": per_platform,
            }
        )
