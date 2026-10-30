"""导出接口的限流。

与 `apps.accounts.security` 的 DB 固定窗口不是一回事：那是登录安全，必须长期
留痕、可回溯；导出要的是便宜的滑动窗口，DRF 的 cache 版本足够。

两条刻意的取舍：

1. **按角色分档**：校管 5 次/时、超管 20 次/时。`SimpleRateThrottle` 原生不支持
   按角色取 rate（`__init__` 里就要算好），因此覆写 `allow_request` 重算。

2. **fail-open**：Redis 抖动时放行并记 warning，而不是抛 500。
   导出是低频管理功能，让基础设施抖动连带打死管理员不可接受；真正的硬闸门是
   DB 里的部分唯一索引（同一 actor 只能有一个未完成任务），不依赖缓存。
"""
import logging

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle

logger = logging.getLogger(__name__)


class _RoleAwareThrottle(SimpleRateThrottle):
    """按用户角色取配额；缓存故障时放行。"""

    scope = "export"
    default_rate = "5/hour"
    # {角色: settings 属性名}；未列出的角色用 default_rate
    role_rate_settings = {}

    def get_rate(self):
        # __init__ 阶段拿不到 request，只能先给保守默认值，
        # 真正的配额在 allow_request 里按角色重算。
        return self.default_rate

    def pick_rate(self, request):
        user = getattr(request, "user", None)
        if getattr(user, "is_super_admin", False):
            role = "super_admin"
        elif getattr(user, "is_school_admin", False):
            role = "school_admin"
        else:
            role = ""
        setting_name = self.role_rate_settings.get(role)
        if not setting_name:
            return self.default_rate
        return getattr(settings, setting_name, self.default_rate)

    def allow_request(self, request, view):
        self.request = request
        self.rate = self.pick_rate(request)
        self.num_requests, self.duration = self.parse_rate(self.rate)
        try:
            return super().allow_request(request, view)
        except Exception:  # noqa: BLE001 - 缓存不可用不应升级成 500
            logger.warning("导出限流缓存不可用，放行本次请求", exc_info=True)
            return True

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": user.pk}


class ExportCreateThrottle(_RoleAwareThrottle):
    scope = "export_create"
    default_rate = "5/hour"
    role_rate_settings = {
        "super_admin": "EXPORT_CREATE_RATE_SUPER_ADMIN",
        "school_admin": "EXPORT_CREATE_RATE_SCHOOL_ADMIN",
    }


class ExportDownloadThrottle(_RoleAwareThrottle):
    scope = "export_download"
    default_rate = "30/hour"
    role_rate_settings = {}  # 下载不分角色，统一配额
