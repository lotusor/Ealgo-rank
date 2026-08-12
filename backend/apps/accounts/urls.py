from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts import views

app_name = "accounts"

router = DefaultRouter()
router.register("platform-accounts", views.PlatformAccountViewSet,
                basename="platform-account")
router.register("notifications", views.NotificationViewSet,
                basename="notification")
router.register("users", views.UserViewSet, basename="user")

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("username-available/", views.UsernameAvailableView.as_view(),
         name="username-available"),
    path("me/", views.MeView.as_view(), name="me"),
    path("change-password/", views.ChangePasswordView.as_view(),
         name="change-password"),
] + router.urls
