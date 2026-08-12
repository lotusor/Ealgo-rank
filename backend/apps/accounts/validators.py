"""用户名规则（本地注册 / passport 首登认领 共用）。

为什么单独成模块：
    用户名有两条写入入口——本地注册 ``RegisterSerializer`` 和 passport 首登
    认领 ``UserUpdateSerializer``，还有一个只读的占用查询接口。三处必须共用
    同一套规则，否则能从不同入口造出格式不一致、甚至互相冲突的用户名。

为什么规则要严：
    ``username`` 是**对外展示字段**——个人排行榜（``ranking`` 序列化器取
    ``user.username``）、管理员审核页的申请人列都直接显示它。所以既要可读，
    也要挡掉冒充官方/管理员的取名。
"""
from __future__ import annotations

import re

from rest_framework import serializers

# 允许：ASCII 字母 / 数字 / 下划线 / 连字符 / 句点，以及常用汉字；长度 3-20。
# 句点与连字符放开是为了兼容 Codeforces 之类平台的常见 handle 写法。
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\u4e00-\u9fff-]{3,20}$")

# 至少含一个「有意义字符」，挡掉 "___" / "..." / "---" 这类纯符号名
_HAS_ALNUM_RE = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]")

# 保留字（小写比较）：防止冒充官方或管理员身份
RESERVED_USERNAMES = frozenset({
    "admin", "admins", "administrator", "root", "superuser", "superadmin",
    "staff", "system", "sys", "official", "support", "help", "helpdesk",
    "service", "security", "moderator", "operator", "master",
    "lotus", "passport", "ealgo", "e-algo", "algorank", "algo-rank",
    "anonymous", "guest", "null", "none", "undefined", "me", "self", "test",
})


def validate_username(value: str, *, exclude_pk: int | None = None) -> str:
    """校验用户名（格式 / 保留字 / 占用），返回去空白后的合法值。

    Args:
        value: 待校验的原始输入。
        exclude_pk: 查重时排除的用户主键。改自己的名字时必须传，否则会把
            自己当成占用者。

    Raises:
        rest_framework.serializers.ValidationError: 任一规则不通过。

    Note:
        查重用 ``__iexact`` 而不是精确匹配。``username`` 的 unique 约束区分
        大小写，只靠它会让 "Alice" 与 "alice" 同时存在——排行榜上两行看着
        几乎一样，也方便冒充。
    """
    # 延迟导入：validators 被 serializers 导入，模型层不应产生反向依赖链
    from apps.accounts.models import User

    value = (value or "").strip()
    if not value:
        raise serializers.ValidationError("请输入用户名")
    if not USERNAME_RE.match(value):
        raise serializers.ValidationError(
            "用户名需为 3-20 个字符，仅允许中文、字母、数字、下划线、连字符和句点")
    if not _HAS_ALNUM_RE.search(value):
        raise serializers.ValidationError("用户名至少需包含一个中文、字母或数字")
    if value.lower() in RESERVED_USERNAMES:
        raise serializers.ValidationError("该用户名为系统保留，请更换")

    qs = User.objects.filter(username__iexact=value)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise serializers.ValidationError("用户名已被占用")
    return value


def first_error_message(exc: serializers.ValidationError) -> str:
    """把 DRF 校验异常压成一句人话，供只读的占用查询接口回给前端。"""
    detail = exc.detail
    if isinstance(detail, (list, tuple)):
        return str(detail[0]) if detail else "用户名不可用"
    if isinstance(detail, dict):
        for v in detail.values():
            if isinstance(v, (list, tuple)) and v:
                return str(v[0])
            return str(v)
    return str(detail)


__all__ = [
    "USERNAME_RE",
    "RESERVED_USERNAMES",
    "validate_username",
    "first_error_message",
]
