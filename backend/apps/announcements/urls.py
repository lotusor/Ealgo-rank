from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.announcements import views

app_name = "announcements"

router = DefaultRouter()
router.register("announcements", views.AnnouncementViewSet, basename="announcement")

# public 必须在 router.urls 之前，否则会被 <pk> 路由抢 matched
urlpatterns = [
    path("announcements/public/", views.AnnouncementPublicView.as_view(),
         name="public"),
] + router.urls
