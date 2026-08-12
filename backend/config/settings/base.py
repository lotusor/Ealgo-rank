"""
公共配置。dev/prod 都从这里继承，只覆盖差异项。
敏感配置一律走环境变量（.env），不写死在代码里。
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# backend/config/settings/base.py -> backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# 仓库根目录，crawlers/ 与 backend/ 平级
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def env_list(key, default=None):
    val = os.environ.get(key)
    if not val:
        return list(default or [])
    return [x.strip() for x in val.split(",") if x.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.schools",
    "apps.contests",
    "apps.crawler",
    "apps.ranking",
    "apps.announcements",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# 自定义用户模型必须在首次 migrate 前就定下来，后期更换代价极高
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- DRF ----------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # 统一认证中心签发的 RS256 JWT（离线验签，按 passport_user_id 解析本地用户）。
        # 子类对本地 HS256 令牌放行给 simplejwt，保证 root/兜底登录并存。
        "apps.accounts.auth.AlgoRankPassportAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "600/min",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "E-algo rank API",
    "DESCRIPTION": "算法竞赛排名系统接口文档",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------- Lotus Passport（统一认证中心）----------
# 仅做身份认证，返回 RS256 JWT；业务权限（role/school/管理员）由本系统维护。
# 生产务必通过环境变量把 BASE_URL 指向 https://passport.eacm.cn。
LOTUS_PASSPORT = {
    "BASE_URL": env("PASSPORT_BASE_URL", "http://127.0.0.1:8000"),
    "ISSUER": env("PASSPORT_ISSUER", "lotus-passport"),
    "AUTO_CREATE_USER": env_bool("PASSPORT_AUTO_CREATE_USER", True),
    "USER_RESOLVER": "apps.accounts.auth.resolve_passport_user",
}

# ---------- JWT ----------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("JWT_ACCESS_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------- Celery ----------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1")
# 连接超时：broker / result store 不可达时快速失败，避免阻塞 Web 请求线程
CELERY_BROKER_CONNECTION_TIMEOUT = 3            # broker 连接超时（秒）
CELERY_BROKER_CONNECTION_MAX_RETRIES = 1        # 仅重试 1 次即放弃
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = False
# socket 级超时：直接作用于 redis 连接，避免卡在 OS 的 TCP connect 超时上
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "socket_connect_timeout": 3,
    "socket_timeout": 3,
}
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
    "socket_connect_timeout": 3,
    "socket_timeout": 3,
}
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 30        # 硬超时 30 分钟
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 25   # 软超时 25 分钟，留时间收尾
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# 牛客抓取最慢（1100 人约 65s），单独队列避免拖垮其他任务
CELERY_TASK_ROUTES = {
    "apps.crawler.tasks.crawl_nowcoder*": {"queue": "crawl_slow"},
    "apps.crawler.tasks.*": {"queue": "crawl"},
    "apps.ranking.tasks.*": {"queue": "default"},
}
# 未显式路由的任务（如 debug_task）落入此默认队列，避免落到 celery 默认名
CELERY_TASK_DEFAULT_QUEUE = "default"
# 生产队列（crawl / crawl_slow / default）首次出现时由 broker 自动建队列
CELERY_TASK_CREATE_MISSING_QUEUES = True

# ---------- CORS ----------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)
CORS_ALLOW_CREDENTIALS = True

# ---------- 业务常量 ----------
# 爬虫脚本目录，crawler app 直接复用已验证的三个爬虫
CRAWLER_DIR = REPO_ROOT / "crawlers"

# 初始超级管理员（首次 migrate 后由 bootstrap 命令创建）
ROOT_ADMIN_USERNAME = env("ROOT_ADMIN_USERNAME", "root")
ROOT_ADMIN_EMAIL = env("ROOT_ADMIN_EMAIL", "root@e-algo-rank.local")
ROOT_ADMIN_PASSWORD = env("ROOT_ADMIN_PASSWORD", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.db.backends": {"level": "WARNING", "handlers": ["console"],
                               "propagate": False},
    },
}
