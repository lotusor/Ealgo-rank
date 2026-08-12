from rest_framework.routers import DefaultRouter

from apps.schools import views

app_name = "schools"

router = DefaultRouter()
router.register("schools", views.SchoolViewSet, basename="school")
router.register("applications", views.SchoolAdminApplicationViewSet,
                basename="school-admin-application")
router.register("score-configs", views.ScoreConfigViewSet,
                basename="score-config")

urlpatterns = router.urls
