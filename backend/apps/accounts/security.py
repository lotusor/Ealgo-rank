"""登录安全核心：失败锁定、频率限制、异常行为检测、设备指纹（NAT 友好）。

设计要点
--------
- 防爆破以「账号维度」+「设备指纹维度」为主，「IP 维度」仅作纵深防御且阈值**刻意放宽**。
  原因：校园网/企业网大量用户共享同一 NAT 出口 IP，纯 IP 限流会误伤整片用户，
  或被攻击者用同一出口绕过。设备指纹（前端 X-Device-Id / UA+语言）能在共享 IP
  下区分不同浏览器/设备，从而精准限流而不波及他人。
- 所有阈值走环境变量，可用 tests 的 override_settings 覆盖。
- 本模块顶层只依赖 settings，模型在函数中惰性导入，避免与 models 形成环依赖。
"""
from __future__ import annotations

import hashlib
import os
from datetime import timedelta

from django.conf import settings
from django.utils import timezone


# ---------- 配置（全部可用环境变量覆盖，见 .env.example）----------
def _get_int(key: str, default: str) -> int:
    val = getattr(settings, key, None)
    if val is None:
        val = os.environ.get(key, default)
    try:
        return int(val)
    except (TypeError, ValueError):
        return int(default)


def get_security_config() -> dict:
    return {
        # 连续失败达此值 → 临时锁定
        "MAX_CONSECUTIVE_FAILURES": _get_int("AUTH_MAX_CONSECUTIVE_FAILURES", "5"),
        # 锁定时长（分钟），到期自动解锁
        "LOCK_DURATION_MINUTES": _get_int("AUTH_LOCK_MINUTES", "15"),
        # 单账号（identifier）失败窗口与上限
        "FAILURE_WINDOW_MINUTES": _get_int("AUTH_FAILURE_WINDOW_MINUTES", "15"),
        "MAX_FAILURES_PER_WINDOW": _get_int("AUTH_MAX_FAILURES_PER_WINDOW", "10"),
        # 设备维度：同一设备指纹在窗口内的登录失败上限（NAT 下区分不同浏览器/设备）
        "DEVICE_LOGIN_MAX": _get_int("AUTH_DEVICE_LOGIN_MAX", "20"),
        "DEVICE_LOGIN_WINDOW_MINUTES": _get_int("AUTH_DEVICE_WINDOW_MINUTES", "10"),
        # IP 维度：共享 NAT 出口必须放宽（默认比设备维度高一个数量级）
        "IP_LOGIN_MAX": _get_int("AUTH_IP_LOGIN_MAX", "300"),
        "IP_LOGIN_WINDOW_MINUTES": _get_int("AUTH_IP_LOGIN_WINDOW_MINUTES", "10"),
        # 登出频率
        "LOGOUT_USER_MAX": _get_int("AUTH_LOGOUT_USER_MAX", "30"),
        "LOGOUT_USER_WINDOW_MINUTES": _get_int("AUTH_LOGOUT_USER_WINDOW_MINUTES", "10"),
        "LOGOUT_SESSION_MAX": _get_int("AUTH_LOGOUT_SESSION_MAX", "10"),
        # 异常检测
        "ANOMALY_DISTINCT_IDS": _get_int("AUTH_ANOMALY_DISTINCT_IDS", "5"),  # 同设备短时试不同账号 → 撞库
        "ANOMALY_TOGGLE_PAIRS": _get_int("AUTH_ANOMALY_TOGGLE_PAIRS", "8"),  # 同用户短时登录/登出反复横跳
    }


# ---------- 客户端识别 ----------
def get_client_ip(request) -> str:
    """取真实客户端 IP。

    信任反向代理（nginx）注入的 X-Forwarded-For，取第一个（真实客户端）。
    校园网场景：这一项往往是整栋/整校共享的 NAT 出口 IP，故 IP 限流必须放宽。
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.META.get("HTTP_X_REAL_IP")
    if xri:
        return xri.strip()
    return request.META.get("REMOTE_ADDR", "")


def get_device_fingerprint(request) -> str:
    """设备指纹：跨 NAT 区分同一出口 IP 下的不同用户/浏览器。

    优先用前端写入 localStorage 的稳定 X-Device-Id（最精准）；缺失时回退到
    User-Agent + Accept-Language 组合（同一校园网不同设备/浏览器通常仍可区分）。
    """
    device_id = (request.headers.get("X-Device-Id") or "").strip()
    if device_id:
        return hashlib.sha256(device_id.encode("utf-8")).hexdigest()[:32]
    ua = request.META.get("HTTP_USER_AGENT", "") or ""
    lang = request.META.get("HTTP_ACCEPT_LANGUAGE", "") or ""
    return hashlib.sha256(f"{ua}|{lang}".encode("utf-8")).hexdigest()[:32]


# ---------- 日志 ----------
def _log(user, event_type, identifier="", ip="", device_fp="", user_agent="", detail=""):
    from .models import AuthLog
    AuthLog.objects.create(
        user=user, event_type=event_type, identifier=identifier,
        ip=ip, device_fp=device_fp, user_agent=user_agent, detail=detail,
    )


def record_blocked(user, identifier, ip, device_fp, user_agent, detail, code=""):
    from .models import AuthEventType
    _log(user, AuthEventType.LOGIN_BLOCKED, identifier=identifier, ip=ip,
         device_fp=device_fp, user_agent=user_agent, detail=detail or code)


def record_login_failure(user, identifier, ip, device_fp, user_agent, detail=""):
    from .models import AuthEventType
    if user is not None:
        was_locked = user.is_locked
        user.register_login_failure()
        if user.is_locked and not was_locked:
            _log(user, AuthEventType.ACCOUNT_LOCKED, identifier=identifier, ip=ip,
                 device_fp=device_fp, user_agent=user_agent,
                 detail=f"连续失败达阈值，锁定至 {user.locked_until:%Y-%m-%d %H:%M}")
    _log(user, AuthEventType.LOGIN_FAILURE, identifier=identifier, ip=ip,
         device_fp=device_fp, user_agent=user_agent, detail=detail)


def record_login_success(user, identifier, ip, device_fp, user_agent):
    from .models import AuthEventType
    _log(user, AuthEventType.LOGIN_SUCCESS, identifier=identifier, ip=ip,
         device_fp=device_fp, user_agent=user_agent)


def record_logout(user, identifier, ip, device_fp, user_agent, detail=""):
    from .models import AuthEventType
    _log(user, AuthEventType.LOGOUT, identifier=identifier, ip=ip,
         device_fp=device_fp, user_agent=user_agent, detail=detail)


# ---------- 限流判定 ----------
def check_login_allowed(identifier, user, ip, device_fp, user_agent=""):
    """返回 (allowed, code, retry_after_seconds, detail)。

    判定顺序：账号锁定 → 账号失败窗口 → 设备失败窗口 → IP 失败窗口 → 撞库检测。
    """
    from .models import AuthEventType, AuthLog
    cfg = get_security_config()
    now = timezone.now()

    # 1) 账号已锁定（不依赖 IP，纯账号维度）
    if user is not None and user.is_locked:
        remaining = int((user.locked_until - now).total_seconds())
        return (False, "account_locked", max(remaining, 0),
                "账号已临时锁定，请稍后再试或由管理员解锁")

    # 2) 账号维度失败窗口（防针对已知用户名的爆破）
    win = now - timedelta(minutes=cfg["FAILURE_WINDOW_MINUTES"])
    if AuthLog.objects.filter(
        event_type=AuthEventType.LOGIN_FAILURE,
        identifier=identifier, created_at__gte=win,
    ).count() >= cfg["MAX_FAILURES_PER_WINDOW"]:
        return (False, "identifier_rate", cfg["FAILURE_WINDOW_MINUTES"] * 60,
                "该账号登录尝试过于频繁，请稍后再试")

    # 3) 设备维度（NAT 友好：区分同一出口 IP 下的不同浏览器/设备）
    if device_fp:
        dwin = now - timedelta(minutes=cfg["DEVICE_LOGIN_WINDOW_MINUTES"])
        if AuthLog.objects.filter(
            event_type=AuthEventType.LOGIN_FAILURE,
            device_fp=device_fp, created_at__gte=dwin,
        ).count() >= cfg["DEVICE_LOGIN_MAX"]:
            return (False, "device_rate", cfg["DEVICE_LOGIN_WINDOW_MINUTES"] * 60,
                    "该设备登录失败过多，请稍后再试")

    # 4) IP 维度（仅兜底/纵深防御；校园网共享出口必须放宽阈值）
    if ip:
        iwin = now - timedelta(minutes=cfg["IP_LOGIN_WINDOW_MINUTES"])
        if AuthLog.objects.filter(
            event_type=AuthEventType.LOGIN_FAILURE,
            ip=ip, created_at__gte=iwin,
        ).count() >= cfg["IP_LOGIN_MAX"]:
            return (False, "ip_rate", cfg["IP_LOGIN_WINDOW_MINUTES"] * 60,
                    "登录尝试过于频繁，请稍后再试")

    # 5) 异常：同设备短时尝试大量不同账号（撞库）
    if device_fp:
        distinct = (AuthLog.objects
                    .filter(event_type=AuthEventType.LOGIN_FAILURE,
                           device_fp=device_fp,
                           created_at__gte=now - timedelta(
                               minutes=cfg["DEVICE_LOGIN_WINDOW_MINUTES"]))
                    .exclude(identifier="")
                    .values("identifier").distinct().count())
        if distinct >= cfg["ANOMALY_DISTINCT_IDS"]:
            return (False, "credential_stuffing", cfg["DEVICE_LOGIN_WINDOW_MINUTES"] * 60,
                    "检测到疑似撞库行为，已临时拦截")

    return (True, "", 0, "")


def check_logout_allowed(user, jti="", ip="", device_fp="", user_agent=""):
    """登出频率限制：按用户 + 按会话（jti）。"""
    from .models import AuthEventType, AuthLog
    cfg = get_security_config()
    now = timezone.now()
    win = now - timedelta(minutes=cfg["LOGOUT_USER_WINDOW_MINUTES"])

    if AuthLog.objects.filter(
        user=user, event_type=AuthEventType.LOGOUT, created_at__gte=win,
    ).count() >= cfg["LOGOUT_USER_MAX"]:
        return (False, "logout_user_rate", cfg["LOGOUT_USER_WINDOW_MINUTES"] * 60,
                "登出操作过于频繁，请稍后再试")

    if jti:
        if AuthLog.objects.filter(
            user=user, event_type=AuthEventType.LOGOUT,
            detail=jti, created_at__gte=win,
        ).count() >= cfg["LOGOUT_SESSION_MAX"]:
            return (False, "logout_session_rate", cfg["LOGOUT_USER_WINDOW_MINUTES"] * 60,
                    "该会话登出过于频繁，请稍后再试")

    return (True, "", 0, "")


def detect_login_logout_oscillation(user) -> bool:
    """同一用户短时内登录成功↔登出反复横跳（疑似会话探测/令牌滥用）。仅记录告警。"""
    from .models import AuthEventType, AuthLog
    cfg = get_security_config()
    if user is None:
        return False
    win = timezone.now() - timedelta(minutes=cfg["LOGOUT_USER_WINDOW_MINUTES"])
    events = list(AuthLog.objects.filter(
        user=user, created_at__gte=win,
        event_type__in=[AuthEventType.LOGIN_SUCCESS, AuthEventType.LOGOUT],
    ).values_list("event_type", flat=True))
    pairs = sum(
        1 for i in range(len(events) - 1)
        if events[i] == AuthEventType.LOGIN_SUCCESS and events[i + 1] == AuthEventType.LOGOUT
    )
    if pairs >= cfg["ANOMALY_TOGGLE_PAIRS"]:
        _log(user, AuthEventType.ANOMALY, identifier=user.username,
             detail="短时内登录/登出反复横跳，疑似会话探测")
        return True
    return False
