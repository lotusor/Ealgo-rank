"""开发环境：SQLite + 宽松 CORS + 详细报错。"""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, env, env_bool

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

CORS_ALLOW_ALL_ORIGINS = True

# 本地没有 nginx（没有 internal location），下载走 Django 直出文件，
# 否则 X-Accel-Redirect 头会被忽略、浏览器拿到 0 字节空响应。
EXPORT_ACCEL_ENABLED = env_bool("EXPORT_ACCEL_ENABLED", False)

# 本地没起 Redis 时可设 CELERY_TASK_ALWAYS_EAGER=1 同步执行任务，方便调试
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "e-algo-rank-dev",
    }
}

if env("DEV_DB_ENGINE") == "postgres":
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "ealgo"),
        "USER": env("DB_USER", "postgres"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "5432"),
    }
