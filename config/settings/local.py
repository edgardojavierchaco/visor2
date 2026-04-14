from .base import *
import os

# ============================
# 🔐 CORE DEV SETTINGS
# ============================

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'default-secret-key')

DEBUG = True

ALLOWED_HOSTS = [
    '0.0.0.0',
    'localhost',
    '127.0.0.1'
]

# ============================
# ⚡ INSTALLED APPS (DEV ONLY)
# ============================

INSTALLED_APPS += [
    'debug_toolbar',
    'django_extensions',
]

# WhiteNoise solo en dev (runserver sin static conflicts)
INSTALLED_APPS = ['whitenoise.runserver_nostatic'] + INSTALLED_APPS

# ============================
# 🧱 MIDDLEWARE (DEV ONLY)
# ============================

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# ============================
# 🧪 DEBUG TOOLBAR
# ============================

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TEMPLATE_CONTEXT': False,
}

INTERNAL_IPS = [
    '127.0.0.1',
    '10.0.2.2',
]

# ============================
# 🚀 CACHE (DEV = REDIS)
# ============================

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get(
            "REDIS_URL",
            "redis://127.0.0.1:6379/1"
        ),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        },
        "KEY_PREFIX": "visor_dev",
        "TIMEOUT": 300,
    }
}

CACHE_TTL = 60 * 5  # 5 minutos