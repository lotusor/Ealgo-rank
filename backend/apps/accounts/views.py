"""
accounts 视图：
- 注册（公开，返回 user + JWT）
- 用户名占用查询（公开只读，注册页与 passport 首登认领页实时提示）
- 个人信息（读 / 改）
- 平台账号（增 / 删 / 查，仅本人）
- 改密
- 站内信（本人列表 / 单条已读 / 全部已读）
"""
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import (
    Notification,
    NotificationType,
    PlatformAccount,
    User,
)
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    NotificationPublishSerializer,
    NotificationSerializer,
    PlatformAccountSerializer,
    RegisterSerializer,
    UserMeSerializer,
    UserRosterSerializer,
    UserUpdateSerializer,
)
from apps.accounts.validators import first_error_message, validate_username
from apps.common.permissions import IsSchoolAdmin, IsSuperAdmin
from config.pagination import StandardPagination


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        data = UserMeSerializer(user, context={"request": request}).data
        return Response({
            "user": data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_201_CREATED)


class UsernameAvailableView(APIView):
    """用户名占用/合法性查询：``GET ?username=xxx``。

    为什么公开：注册页（未登录）和 passport 首登认领页（已登录）都要用它做
    实时提示。为了不把它变成用户名枚举器，挂了 anon/user 限流
    （见 settings ``DEFAULT_THROTTLE_RATES``：anon 60/min、user 600/min）。

    响应：``{"username": str, "available": bool, "reason": str}``
    ``reason`` 在 ``available=False`` 时给出可直接展示的中文原因。
    """

    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    def get(self, request):
        raw = (request.query_params.get("username") or "").strip()
        # 已登录用户查自己现有的名字不该显示「已占用」
        exclude_pk = request.user.pk if request.user.is_authenticated else None
        try:
            value = validate_username(raw, exclude_pk=exclude_pk)
        except drf_serializers.ValidationError as exc:
            return Response({
                "username": raw,
                "available": False,
                "reason": first_error_message(exc),
            })
        return Response({"username": value, "available": True, "reason": ""})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserMeSerializer(request.user,
                                       context={"request": request})
        return Response(serializer.data)

    def put(self, request):
        serializer = UserUpdateSerializer(
            request.user, data=request.data,
            context={"request": request}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            UserMeSerializer(request.user, context={"request": request}).data)


class PlatformAccountViewSet(viewsets.ModelViewSet):
    """平台账号绑定。只允许 增/删/查，不允许改 handle（改了会破坏归属唯一性）。"""

    serializer_class = PlatformAccountSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return PlatformAccount.objects.filter(
            user=self.request.user).select_related("school")

    def get_serializer_context(self):
        return {"request": self.request}


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "密码已修改"}, status=status.HTTP_200_OK)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """站内信，仅本人可见。"""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get("unread") == "1":
            qs = qs.filter(is_read=False)
        return qs

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        note = self.get_object()
        note.mark_read()
        return Response(
            NotificationSerializer(note, context={"request": request}).data)

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        self.get_queryset().filter(is_read=False).update(
            is_read=True, read_at=timezone.now())
        return Response({"detail": "已全部标记为已读"})

    @action(detail=False, methods=["post"], permission_classes=[IsSuperAdmin])
    def publish(self, request):
        """超级管理员主动发布站内信：可指定接收人，省略则全站广播。"""
        ser = NotificationPublishSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        user_ids = data.get("user_ids") or []
        qs = User.objects.all()
        if user_ids:
            qs = qs.filter(id__in=user_ids)
        notes = [
            Notification(
                user=u,
                type=NotificationType.ADMIN_MESSAGE,
                title=data["title"],
                message=data.get("message", ""),
                link=data.get("link", ""),
            )
            for u in qs
        ]
        created = Notification.objects.bulk_create(notes)
        return Response({"count": len(created)}, status=status.HTTP_201_CREATED)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """管理后台成员名单：学校管理员仅见本校成员，超管可见全部并可按学校筛选。"""

    serializer_class = UserRosterSerializer
    permission_classes = [IsSchoolAdmin]
    pagination_class = StandardPagination
    ordering = ["-date_joined"]

    def get_queryset(self):
        qs = User.objects.annotate(
            platform_accounts_count=Count("platform_accounts"))
        user = self.request.user
        if not user.is_super_admin:
            qs = qs.filter(school_id=user.school_id)

        qp = self.request.query_params
        if qp.get("school"):
            qs = qs.filter(school_id=qp["school"])
        if qp.get("role"):
            qs = qs.filter(role=qp["role"])
        if qp.get("keyword"):
            kw = qp["keyword"]
            qs = qs.filter(
                Q(username__icontains=kw) | Q(real_name__icontains=kw))
        return qs
