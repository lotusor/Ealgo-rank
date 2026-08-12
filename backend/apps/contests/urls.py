"""比赛 / 参赛记录路由。"""
from rest_framework.routers import DefaultRouter

from apps.contests import views

app_name = "contests"

router = DefaultRouter()
router.register("contests", views.ContestViewSet, basename="contest")
router.register("participations", views.ParticipationViewSet,
                basename="participation")
router.register("me/participations", views.MyParticipationViewSet,
                basename="my-participation")

urlpatterns = router.urls
