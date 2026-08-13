"""
accounts 序列化器。
职责：注册、个人信息读写、平台账号绑定、改密、站内信。
注意：
- 平台账号绑定后必须触发 rebind_unbound_participations，回填历史成绩
- 用户变更学校后必须调 sync_platform_accounts_school，把学校同步到名下平台账号
- 用户名规则统一走 apps.accounts.validators，注册与 passport 首登认领共用
"""
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

    class Meta:
        model = PlatformAccount
        fields = ["id", "platform", "platform_display", "handle", "display_name",
                  "verified", "verified_at", "school", "created_at"]
        read_only_fields = ["verified", "verified_at", "school", "created_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None
        platform = attrs.get("platform")
        handle = (attrs.get("handle") or "").strip()
        if platform and handle and user is not None:
            # 一个用户在同一平台只能绑一个账号（uniq_user_platform 兜底）
            if PlatformAccount.objects.filter(user=user, platform=platform).exists():
                raise serializers.ValidationError(
                    {"platform": "你已在该平台绑定过账号，请先解绑再重新绑定"})
            # 跨用户：同一平台账号(handle)只能被一个人绑定
            if PlatformAccount.objects.filter(
                    platform=platform, handle_lower=handle.lower()).exists():
                raise serializers.ValidationError(
                    {"handle": "该平台账号已被其他用户绑定，无法重复绑定"})
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["user"] = None  # 占位，下面赋值
        validated_data["user"] = request.user
        pa = super().create(validated_data)
        # 回填历史上无人认领的参赛记录（作弊记录不解除排除）
        try:
            from apps.crawler.ingest import rebind_unbound_participations
            rebind_unbound_participations(pa)
        except Exception:  # 历史数据缺失不应阻断绑定
            pass
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

    class Meta:
        model = User
        fields = ["id", "username", "email", "real_name", "student_no",
                  "role", "role_display", "school", "school_bound_at",
                  "platform_accounts", "is_super_admin", "is_school_admin",
                  "needs_username", "date_joined"]
        read_only_fields = fields


class UserUpdateSerializer(serializers.ModelSerializer):
    """个人信息更新：用户名认领、真实姓名、学号、绑定/变更学校。"""

    username = serializers.CharField(
        required=False, allow_blank=True,
        help_text="仅 passport 首登占位用户名未认领时可写（一次性）；已认领后不可修改")
    school_code = serializers.CharField(
        required=False, allow_blank=True, write_only=True,
        help_text="可选；不传或空字符串表示不修改；传入已存在的 code 则变更学校并同步平台账号")

    class Meta:
        model = User
        fields = ["username", "real_name", "student_no", "school_code"]

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
    old_password = serializers.CharField(write_only=True)
    new_password1 = serializers.CharField(write_only=True,
                                          validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("原密码错误")
        return value

    def validate(self, attrs):
        if attrs["new_password1"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "两次密码不一致"})
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
