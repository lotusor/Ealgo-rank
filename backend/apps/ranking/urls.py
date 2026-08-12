from rest_framework.routers import DefaultRouter

from apps.ranking import views

app_name = "ranking"

router = DefaultRouter()
router.register("rankings", views.RankSnapshotViewSet, basename="rank-snapshot")

urlpatterns = router.urls
