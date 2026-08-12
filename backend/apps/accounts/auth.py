"""Lotus Passport 用户解析器（接入 algo_rank）。

被 ``lotus_passport.integrations.drf.PassportAuthentication`` 调用，
把一个已验签的 passport 身份解析成本地 ``accounts.User``。

为什么必须自定义（不能用 SDK 默认 resolver）：
    algo_rank 的 ``User`` 继承 ``AbstractUser``，``username`` 是**必填且唯一**的。
    SDK 默认 resolver 只写 ``passport_user_id`` + ``email``，建用户会因缺
    ``username`` 失败。这里用稳定的 ``passport_user_id``(UUID) 充当 username 占位，
    并标记无本地密码（密码登录仅留作 root 紧急兜底，见 bootstrap）。

业务权限（role / school / 管理员）一律由 algo_rank 自己维护，passport 只给身份。
"""
from __future__ import annotations

import base64
import json
from typing import Any

from django.contrib.auth import get_user_model

from lotus_passport.integrations.drf import (
    PassportAuthentication as _PassportAuthentication,
)
from lotus_passport.integrations.drf import get_client


def _jwt_alg(token: str | None) -> str | None:
    """读取 JWT 头里的 alg（不验签），用于把本地 HS256 令牌让给 simplejwt。"""
    if not token or "." not in token:
        return None
    try:
        raw = token.split(".")[0]
        pad = "=" * (-len(raw) % 4)
        return json.loads(base64.urlsafe_b64decode(raw + pad)).get("alg")
    except Exception:
        return None


class AlgoRankPassportAuthentication(_PassportAuthentication):
    """passport RS256 优先；本地 simplejwt 的 HS256 令牌放行给下一个认证类。

    为什么需要这层：两个认证类都会对「类型不符」的令牌抛异常，单纯调整顺序
    无法并存。这里在验签前先看 alg——RS256 才交给父类走 JWKS 离线验签；
    其余（本地 HS256）直接返回 None，由 simplejwt 处理（root/兜底）。
    算法混淆攻击（用 RSA 公钥当 HMAC 密钥签 HS256）仍被 SDK 拒，因为 HS256
    令牌在此被放行给 simplejwt，而 simplejwt 用自身 SECRET_KEY 验签必然失败。
    """

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION")
        token = get_client().extract_bearer(header)
        if token is None:
            return None
        if _jwt_alg(token) != "RS256":
            return None  # 本地 HS256 令牌，交给 simplejwt
        return super().authenticate(request)


def resolve_passport_user(identity) -> Any:
    """按 ``passport_user_id`` 关联/创建本地用户。

    Args:
        identity: ``lotus_passport.types.PassportIdentity``（已离线验签）。
    """
    User = get_user_model()
    pid = str(identity.passport_user_id)

    user = User.objects.filter(passport_user_id=pid).first()
    if user is not None:
        return user

    # 首次通过 passport 登录：自动建本地账号，无本地密码。
    user = User(
        passport_user_id=pid,
        username=pid,  # AbstractUser.username 必填；UUID 唯一且合法
        email=identity.email or "",
    )
    user.set_unusable_password()
    user.save()
    return user
