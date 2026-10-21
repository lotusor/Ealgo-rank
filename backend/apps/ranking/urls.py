from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.ranking import views

app_name = "ranking"

router = DefaultRouter()
router.register("rankings", views.RankSnapshotViewSet, basename="rank-snapshot")

urlpatterns = [
    path("season/", views.SeasonView.as_view(), name="season"),
    path("season/past/", views.SeasonView.as_view(), {"past": True},
         name="season-past"),
    path("me/best/", views.MyBestRecordView.as_view(), name="me-best"),
    path("rating-history/", views.RatingHistoryView.as_view(),
         name="rating-history"),
] + router.urls
