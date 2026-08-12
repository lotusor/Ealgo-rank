"""排名快照列表的缓存层。

设计要点（与用户确认）：
- 缓存 ReadOnly 列表接口"序列化后的分页结果"（school/user 嵌套序列化最贵）。
- 用版本号 `ranking:snapshot:version` 做失效：每次重算后自增，旧缓存自然失效；
  再叠一个 TTL 兜底，避免重算极频繁时孤儿 key 堆积过久。
- 全部读写包 try/except 降级：Redis 不可用时直接回退到查库，绝不拖垮接口。
- 缓存后端跟随 settings：生产 RedisCache、开发 LocMemCache，两层都生效。
"""
import hashlib

from django.core.cache import cache

RANKING_VERSION_KEY = "ranking:snapshot:version"
RANKING_CACHE_TTL = 300  # 5 分钟兜底，重算后版本号自增即真正失效


def get_ranking_version() -> int:
    """当前榜单版本号，默认 0。Redis 异常时返回 0（等于不命中缓存）。"""
    try:
        v = cache.get(RANKING_VERSION_KEY)
        return int(v) if v is not None else 0
    except Exception:
        return 0


def bump_ranking_version() -> int:
    """重算完成后调用：版本号 +1，使所有旧列表缓存失效。

    返回最新版本号；Redis 异常时静默返回 0（不影响重算主流程）。
    """
    try:
        try:
            return cache.incr(RANKING_VERSION_KEY)
        except ValueError:
            # 键不存在时 incr 抛 ValueError，初始化为 1
            cache.set(RANKING_VERSION_KEY, 1, timeout=None)
            return 1
    except Exception:
        return 0


def ranking_cache_key(version: int, request) -> str:
    """按 版本号 + 归一化查询参数 生成缓存 key。

    覆盖 get_queryset 的全部筛选维度（scope/period/school/user）
    与分页维度（page/page_size），保证不同请求命中各自缓存。
    """
    params = sorted(request.query_params.lists())
    flat = "&".join(f"{k}={','.join(v)}" for k, v in params)
    raw = f"v{version}|{flat}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"ranking:list:{digest}"


def safe_cache_get(key):
    try:
        return cache.get(key)
    except Exception:
        return None


def safe_cache_set(key, value, timeout: int) -> None:
    try:
        cache.set(key, value, timeout)
    except Exception:
        pass
