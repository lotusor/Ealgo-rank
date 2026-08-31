from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (SpectacularAPIView, SpectacularSwaggerView)
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenVerifyView

from apps.accounts.views import LoginView, LogoutView, StampedTokenRefreshView


def healthz(_request):
    return JsonResponse({"status": "ok"})


api_v1 = [
    path("healthz/", healthz, name="healthz"),
    path("auth/token/", LoginView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", StampedTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.schools.urls")),
    path("", include("apps.contests.urls")),
    path("", include("apps.ranking.urls")),
    path("", include("apps.crawler.urls")),
    path("", include("apps.announcements.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz, name="healthz"),
    path("api/v1/", include((api_v1, "api"), namespace="v1")),
    # 接口文档含全量 API 结构：仅登录用户可见，避免匿名枚举攻击面
    path("api/schema/",
         SpectacularAPIView.as_view(permission_classes=[IsAuthenticated]),
         name="schema"),
    path("api/docs/",
         SpectacularSwaggerView.as_view(
             url_name="schema", permission_classes=[IsAuthenticated]),
         name="docs"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
