"""
accounts 序列化器。
职责：注册、个人信息读写、平台账号绑定、改密、站内信。
注意：
- 平台账号绑定后必须触发 rebind_unbound_participations，回填历史成绩
- 用户变更学校后必须调 sync_platform_accounts_school，把学校同步到名下平台账号
- 用户名规则统一走 apps.accounts.validators，注册与 passport 首登认领共用
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import Notification, PlatformAccount, User
from apps.accounts.validators import validate_username as validate_username_value
from apps.schools.models import School


class SchoolMinimalSerializer(serializers.ModelSerializer):
    """嵌入用的学校精简信息。"""

    class Meta:
        model = School
        fields = ["id", "name", "short_name", "code"]


class PlatformAccountSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(source="get_platform_display",
                                              read_only=True)
    school = SchoolMinimalSerializer(read_only=True)
    # 前端据此判断能否修改 handle：一周内改过则展示「下次可改时间」
    can_edit_handle = serializers.SerializerMethodField()
    handle_next_edit_at = serializers.SerializerMethodField()

    class Meta:
        model = PlatformAccount
        fields = ["id", "platform", "platform_display", "handle", "display_name",
                  "verified", "verified_at", "school", "created_at",
                  "can_edit_handle", "handle_next_edit_at"]
        read_only_fields = ["verified", "verified_at", "school", "created_at",
                            "can_edit_handle", "handle_next_edit_at"]

    def get_can_edit_handle(self, obj):
        """一周内改过 handle 则不可再改。"""
        return self._next_edit_at(obj) is None

    def get_handle_next_edit_at(self, obj):
        return self._next_edit_at(obj)

    def _next_edit_at(self, obj):
        if obj.handle_changed_at is None:
            return None
        return obj.handle_changed_at + timedelta(
            days=settings.PLATFORM_HANDLE_EDIT_COOLDOWN_DAYS)

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None
        # PATCH 时可能只传 handle，platform 需回退到 instance
        platform = attrs.get("platform") or (
            self.instance.platform if self.instance else None)
        handle = (attrs.get("handle") or "").strip()
        is_create = self.instance is None
        if platform and handle and user is not None:
            # 一个用户在同一平台只能绑一个账号（uniq_user_platform 兜底）
            if is_create and PlatformAccount.objects.filter(
                    user=user, platform=platform).exists():
                raise serializers.ValidationError(
                    {"platform": "你已在该平台绑定过账号，请先解绑再重新绑定"})
            # 跨用户：同一平台账号(handle)只能被一个人绑定
            if PlatformAccount.objects.filter(
                    platform=platform, handle_lower=handle.lower()
            ).exclude(pk=self.instance.pk if self.instance else None).exists():
                raise serializers.ValidationError(
                    {"handle": "该平台账号已被其他用户绑定，无法重复绑定"})
        return attrs

    def update(self, instance, validated_data):
        # 修改 handle 受「一周一次」冷却限制
        new_handle = (validated_data.get("handle") or "").strip()
        old_handle = (instance.handle or "").strip()
        if new_handle and new_handle.lower() != old_handle.lower():
            next_at = self._next_edit_at(instance)
            if next_at is not None:
                raise serializers.ValidationError(
                    {"handle": f"平台账号 ID 一周仅可修改一次，请于 "
                               f"{timezone.localtime(next_at):%Y-%m-%d %H:%M} 后再试"})
            validated_data["handle_changed_at"] = timezone.now()
        return super().update(instance, validated_data)

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["user"] = None  # 占位，下面赋值
        validated_data["user"] = request.user
        pa = super().create(validated_data)
        # 回填历史上无人认领的参赛记录（作弊记录不解除排除）
        try:
            from apps.crawler.ingest import rebind_unbound_participations
            rebound = rebind_unbound_participations(pa)
            if rebound:
                # 回填的历史成绩立即生效：异步重算排名，不等次日爬虫
                from apps.accounts.views import _dispatch_recompute
                _dispatch_recompute()
        except Exception:  # 历史数据缺失不应阻断绑定
            pass
        # 定向补数：官方历史索引 → 站内缺失场次 → rating 涨落，交给 Celery 任务。
        # helper 内部已吞异常并记日志；派发失败只影响时效，
        # 每日牛客历史巡检（nowcoder-history-sweep）会兜住。
        from apps.crawler.tasks import dispatch_account_history_backfill
        dispatch_account_history_backfill(pa.pk)
        return pa


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True,
                                     validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    school_code = serializers.CharField(
        required=False, allow_blank=True, write_only=True,
        help_text="可选，按学校 code 绑定学校")

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "password2",
                  "real_name", "student_no", "school_code"]

    def validate_username(self, value):
        # 与 passport 首登认领共用同一套规则（格式 / 保留字 / 大小写不敏感查重）
        return validate_username_value(value)

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("邮箱已被注册")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "两次密码不一致"})
        return attrs

    def create(self, validated_data):
        school_code = (validated_data.pop("school_code", "") or "").strip()
        validated_data.pop("password2")
        password = validated_data.pop("password")
        school = None
        if school_code:
            school = School.objects.filter(code=school_code).first()
        user = User(**validated_data)
        user.set_password(password)
        if school:
            user.school = school
            user.school_bound_at = timezone.now()
        user.save()
        return user


class UserMeSerializer(serializers.ModelSerializer):
    """当前用户只读信息，含角色展示与平台账号。"""

    role_display = serializers.CharField(source="get_role_display", read_only=True)
    school = SchoolMinimalSerializer(read_only=True)
    platform_accounts = PlatformAccountSerializer(many=True, read_only=True)
    is_super_admin = serializers.BooleanField(read_only=True)
    is_school_admin = serializers.BooleanField(read_only=True)
    # 前端据此判断补全页的用户名框是否可编辑，并把它纳入「资料是否补全」的门槛
    needs_username = serializers.BooleanField(read_only=True)
    # 是否已设置本地密码：passport 首登用户为 False，可走「设置本地密码」流程
    has_usable_password = serializers.BooleanField(read_only=True)
    # 头像：有则输出完整 URL，无则 null（前端据此回退到首字母头像）
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "real_name", "student_no",
                  "avatar", "bio", "role", "role_display", "school",
                  "school_bound_at", "platform_accounts", "is_super_admin",
                  "is_school_admin", "needs_username", "has_usable_password",
                  "date_joined"]
        read_only_fields = fields

    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get("request")
        url = obj.avatar.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class UserUpdateSerializer(serializers.ModelSerializer):
    """个人信息更新：用户名认领、真实姓名、学号、头像、个性签名、绑定/变更学校。"""

    username = serializers.CharField(
        required=False, allow_blank=True,
        help_text="仅 passport 首登占位用户名未认领时可写（一次性）；已认领后不可修改")
    school_code = serializers.CharField(
        required=False, allow_blank=True, write_only=True,
        help_text="可选；不传或空字符串表示不修改；传入已存在的 code 则变更学校并同步平台账号")
    avatar = serializers.ImageField(
        required=False, allow_null=True,
        help_text="头像图片；传 null 表示移除头像")

    def validate_avatar(self, f):
        if f and f.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("头像图片不能超过 2MB")
        return f

    class Meta:
        model = User
        fields = ["username", "real_name", "student_no", "school_code",
                  "avatar", "bio"]

    def validate_username(self, value):
        """未认领 → 按统一规则校验；已认领 → 只允许原值回传，否则拒绝。

        允许原值回传是因为前端补全表单可能整表提交（含 readonly 的用户名），
        不该因此报错；但任何**实际改名**都要挡掉——用户名是排行榜与管理员审核
        页的展示身份，改名会让历史记录对不上人。
        """
        value = (value or "").strip()
        user = self.instance
        if not value or user is None:
            return ""
        if not user.needs_username:
            if value.lower() != (user.username or "").lower():
                raise serializers.ValidationError("用户名不可修改")
            return ""  # 原值回传，视作未修改
        return validate_username_value(value, exclude_pk=user.pk)

    def validate_school_code(self, value):
        value = (value or "").strip()
        if not value:
            return value
        if not School.objects.filter(code=value).exists():
            raise serializers.ValidationError("学校 code 不存在")
        return value

    def update(self, instance, validated_data):
        school_code = validated_data.pop("school_code", "")
        school_code = (school_code or "").strip()
        # validate_username 已把「无需变更」的情形归一化成空串
        new_username = (validated_data.pop("username", "") or "").strip()
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if new_username:
            instance.username = new_username
        if school_code:
            new_school = School.objects.get(code=school_code)
            if instance.school_id != new_school.id:
                instance.school = new_school
                instance.school_bound_at = timezone.now()
                # 关键：学校变了，名下平台账号归属必须同步，否则历史成绩挂旧学校
                instance.sync_platform_accounts_school()
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """改密 / 设置本地密码（二合一）。

    - 已设置本地密码的用户：必须提供并校验原密码。
    - passport 首登用户（``has_usable_password()`` 为 False，尚未设本地密码）：
      无需原密码，直接设置首条本地密码。
    """

    old_password = serializers.CharField(write_only=True, required=False)
    new_password1 = serializers.CharField(write_only=True,
                                          validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password1"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "两次密码不一致"})
        user = self.context["request"].user
        # 已设置本地密码才校验原密码；passport 首登用户（无本地密码）跳过
        if user.has_usable_password():
            old = attrs.get("old_password")
            if not old:
                raise serializers.ValidationError({"old_password": "请输入原密码"})
            if not user.check_password(old):
                raise serializers.ValidationError({"old_password": "原密码错误"})
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password1"])
        user.save()
        return user


class UserRosterSerializer(serializers.ModelSerializer):
    """管理后台成员名单：核心属性 + 平台账号数。"""
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    school_name = serializers.CharField(source="school.name", read_only=True,
                                        default="")
    school_code = serializers.CharField(source="school.code", read_only=True,
                                        default="")
    platform_accounts_count = serializers.IntegerField(read_only=True)
    is_super_admin = serializers.BooleanField(read_only=True)
    is_school_admin = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "real_name", "student_no",
                  "role", "role_display", "school", "school_name", "school_code",
                  "school_bound_at", "platform_accounts_count",
                  "is_super_admin", "is_school_admin", "date_joined"]
        read_only_fields = fields


class UserPublicProfileSerializer(serializers.ModelSerializer):
    """用户公开信息页：榜单点击跳转后展示的个性信息 + 竞赛信息。

    公开可读（不含邮箱/学号等隐私字段），展示头像、签名、各平台 rating 与参赛记录。
    """
    avatar = serializers.SerializerMethodField()
    school_name = serializers.CharField(source="school.name", read_only=True,
                                        default="")
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    platforms = serializers.SerializerMethodField()
    platform_ratings = serializers.SerializerMethodField()
    participations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "real_name", "avatar", "bio", "school",
                  "school_name", "role_display", "platforms",
                  "platform_ratings", "participations"]
        read_only_fields = fields

    def get_platforms(self, obj):
        """已绑定的平台名（不含 handle 等标识）——供前端固定折线图选项卡，
        避免账号已绑定但暂无 rated 成绩时整个平台入口消失。"""
        return list(obj.platform_accounts.order_by("platform")
                    .values_list("platform", flat=True))

    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get("request")
        url = obj.avatar.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_platform_ratings(self, obj):
        """各平台当前 rating（该平台最新一场的 new_rating）与最近一次涨跌。"""
        from apps.contests.models import Participation

        ratings = []
        for acc in obj.platform_accounts.all():
            p = (Participation.objects
                 .filter(platform_account=acc, new_rating__isnull=False)
                 .select_related("contest")
                 .order_by("-contest__start_time").first())
            if p is None:
                continue
            ratings.append({
                "platform": acc.platform,
                "handle": acc.handle,
                "rating": p.new_rating,
                "delta": p.rating_delta,
            })
        return ratings

    def get_participations(self, obj):
        """公开的参赛记录（未排除的场次 + rating 涨跌）。

        不按 `contest.is_rated` 过滤：牛客个人主页的参赛记录本就包含不计 Rating 的
        校内赛/同步赛，本站口径与之对齐（这类行来自 profile_joined，
        `countable()` 会把它们挡在积分之外，所以展示放宽不影响任何计分口径）。
        """
        from apps.contests.models import Participation
        from apps.contests.serializers import MyParticipationSerializer

        qs = (Participation.objects
              .filter(platform_account__user=obj, is_excluded=False)
              .select_related("contest", "platform_account")
              .order_by("-contest__start_time"))
        return MyParticipationSerializer(qs, many=True,
                                         context=self.context).data


class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "type", "type_display", "title", "message", "link",
                  "is_read", "created_at"]
        read_only_fields = fields


class NotificationPublishSerializer(serializers.Serializer):
    """超级管理员主动发布站内信：可指定接收人，省略则全站广播。"""

    title = serializers.CharField(max_length=120, help_text="站内信标题")
    message = serializers.CharField(required=False, allow_blank=True, default="",
                                    help_text="正文内容")
    link = serializers.CharField(required=False, allow_blank=True, max_length=255,
                                 default="", help_text="可选跳转链接（前端路由）")
    user_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True,
        help_text="接收用户 ID 列表；省略或为空表示全站广播")
