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
from rest_framework_simplejwt.views import TokenRefreshView

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
    UserPublicProfileSerializer,
    UserRosterSerializer,
    UserUpdateSerializer,
)
from apps.accounts.security import (
    check_login_allowed,
    check_logout_allowed,
    detect_login_logout_oscillation,
    get_client_ip,
    get_device_fingerprint,
    record_blocked,
    record_login_failure,
    record_login_success,
    record_logout,
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


class LoginView(APIView):
    """账号密码登录（替代 simplejwt 默认 TokenObtainPairView）。

    在密码校验前先做「锁定 / 限流」预检，失败后再记录并尝试锁定。
    限流/锁定以「账号维度 + 设备指纹维度」为主，「IP 维度」仅兜底且阈值放宽，
    以适配校园网等共享 NAT 出口（详见 HANDOFF.md 登录安全章节）。
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # 登录接口本身不需要已认证

    def post(self, request):
        identifier = (request.data.get("username")
                      or request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        ip = get_client_ip(request)
        device_fp = get_device_fingerprint(request)
        ua = request.META.get("HTTP_USER_AGENT", "")

        user = None
        if identifier:
            user = (User.objects.filter(username=identifier).first()
                    or User.objects.filter(email=identifier).first())

        allowed, code, retry_after, detail = check_login_allowed(
            identifier, user, ip, device_fp, ua)
        if not allowed:
            record_blocked(user, identifier, ip, device_fp, ua, detail, code)
            # 锁定态统一返回 423（与失败后判定的路径保持一致）
            if code == "account_locked":
                return self._error(
                    code, detail, retry_after, status=status.HTTP_423_LOCKED)
            return self._error(code, detail, retry_after)

        # 密码校验
        if user is not None and user.check_password(password):
            user.register_login_success()
            record_login_success(user, identifier, ip, device_fp, ua)
            detect_login_logout_oscillation(user)
            refresh = RefreshToken.for_user(user)
            refresh["security_stamp"] = user.security_stamp
            access = refresh.access_token
            access["security_stamp"] = user.security_stamp
            data = {
                "user": UserMeSerializer(user,
                                         context={"request": request}).data,
                "access": str(access),
                "refresh": str(refresh),
            }
            return Response(data, status=status.HTTP_200_OK)

        # 失败
        record_login_failure(user, identifier, ip, device_fp, ua,
                             "用户名或密码错误")
        if user is not None and user.is_locked:
            remaining = int((user.locked_until
                             - timezone.now()).total_seconds())
            cfg = _lock_minutes()
            return self._error(
                "account_locked",
                f"连续登录失败次数过多，账号已锁定 {cfg} 分钟", max(remaining, 0),
                status=status.HTTP_423_LOCKED)
        return self._error("invalid_credentials", "用户名或密码错误", 0,
                           status=status.HTTP_401_UNAUTHORIZED)

    @staticmethod
    def _error(code, detail, retry_after, status=status.HTTP_429_TOO_MANY_REQUESTS):
        resp = Response({"detail": detail, "code": code}, status=status)
        if retry_after:
            resp["Retry-After"] = str(retry_after)
        return resp


def _lock_minutes() -> int:
    from apps.accounts.security import get_security_config
    return get_security_config()["LOCK_DURATION_MINUTES"]


class StampedTokenRefreshView(TokenRefreshView):
    """刷新访问令牌时把当前 ``security_stamp`` 写回新令牌，保证登出全部设备能吊销它。"""

    def post(self, request, *args, **kwargs):
        resp = super().post(request, *args, **kwargs)
        raw = resp.data.get("access")
        if raw:
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                access = AccessToken(raw)
                user_id = access.get("user_id")
                if user_id is not None:
                    user = User.objects.filter(pk=user_id).first()
                    if user is not None:
                        access["security_stamp"] = user.security_stamp
                        resp.data["access"] = str(access)
            except Exception:
                pass
        return resp


class LogoutView(APIView):
    """登出：吊销当前 refresh 令牌（黑名单）+ 可选登出全部设备（轮换安全戳）。

    按用户与按会话（jti）双重频率限制，防登出接口被刷。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        ip = get_client_ip(request)
        device_fp = get_device_fingerprint(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        jti = ""
        if getattr(request, "auth", None) and hasattr(request.auth, "get"):
            jti = request.auth.get("jti") or ""

        allowed, code, retry_after, detail = check_logout_allowed(
            user, jti=jti, ip=ip, device_fp=device_fp, user_agent=ua)
        if not allowed:
            record_blocked(user, user.username, ip, device_fp, ua, detail, code)
            return Response({"detail": detail, "code": code},
                            status=status.HTTP_429_TOO_MANY_REQUESTS,
                            headers={"Retry-After": str(retry_after)}
                            if retry_after else None)

        refresh_token = request.data.get("refresh") or ""
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except Exception:
                pass

        # 同时兼容 JSON(true→Python bool) 与表单("True"/"1"→字符串) 两种传参
        raw_all = request.data.get("all")
        all_devices = raw_all is True or str(raw_all).lower() in (
            "true", "1", "yes", "on")
        if all_devices:
            user.rotate_security_stamp()

        record_logout(user, user.username, ip, device_fp, ua,
                      detail=jti or ("all" if all_devices else ""))
        detect_login_logout_oscillation(user)

        tip = "已登出全部设备" if all_devices else "已登出"
        return Response({"detail": tip}, status=status.HTTP_200_OK)


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
    """平台账号绑定。支持 增/删/查 + 改 handle（一周一次冷却，见 serializer）。"""

    serializer_class = PlatformAccountSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        return PlatformAccount.objects.filter(
            user=self.request.user).select_related("school")

    def get_serializer_context(self):
        return {"request": self.request}

    def update(self, request, *args, **kwargs):
        """PATCH：仅允许改 handle / display_name；platform 不允许改（改平台应解绑重绑）。"""
        partial = kwargs.pop("partial", True)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        # 改 handle 后回填历史成绩 + 异步补全参与比赛索引（与创建时一致）
        handle_changed = (
            "handle" in serializer.validated_data and
            (serializer.validated_data["handle"] or "").strip().lower() !=
            instance.handle_lower
        )
        self.perform_update(serializer)
        if handle_changed:
            try:
                from apps.crawler.ingest import (
                    rebind_unbound_participations,
                    fill_participated_contests_async,
                )
                rebind_unbound_participations(instance)
                fill_participated_contests_async(instance.pk)
            except Exception:  # 历史数据缺失不应阻断修改
                pass
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # 改密即吊销该账号所有其他会话（轮换安全戳），防止旧令牌继续可用
        request.user.rotate_security_stamp()
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


class UserPublicProfileView(APIView):
    """用户公开信息页：榜单点击跳转后展示个性信息 + 竞赛信息（任何人可读）。"""

    permission_classes = [AllowAny]

    def get(self, request, pk):
        from django.shortcuts import get_object_or_404
        user = get_object_or_404(User.objects.select_related("school"), pk=pk)
        data = UserPublicProfileSerializer(
            user, context={"request": request}).data
        return Response(data)
