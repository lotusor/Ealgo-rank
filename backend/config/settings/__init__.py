"""
settings 包。默认加载 dev，通过环境变量 DJANGO_ENV=prod 切到生产配置。
也可以直接指定 DJANGO_SETTINGS_MODULE=config.settings.prod。
"""

import os

_env = os.environ.get("DJANGO_ENV", "dev").strip().lower()

if _env in ("prod", "production"):
    from .prod import *  # noqa: F401,F403
else:
    from .dev import *  # noqa: F401,F403
