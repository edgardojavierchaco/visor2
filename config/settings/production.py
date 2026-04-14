from .base import *
import os

# ============================
# 🔐 CORE SECURITY
# ============================

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

DEBUG = False

ALLOWED_HOSTS = [
    'visoreducativochaco.com.ar',
    'www.visoreducativochaco.com.ar',
    'localhost',
    '127.0.0.1',
]

# ============================
# 🔒 SECURITY HEADERS
# ============================

SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', 'True').lower() == 'True'

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', 3600))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

X_FRAME_OPTIONS = 'DENY'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

CSRF_TRUSTED_ORIGINS = [
    'https://visoreducativochaco.com.ar',
    'https://www.visoreducativochaco.com.ar',
]

# ============================
# 🧱 INSTALLED APPS (PROD ONLY FIXES)
# ============================

# WhiteNoise en producción
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================
# ⚡ CACHE REDIS (PROD)
# ============================

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        },
        "KEY_PREFIX": "visor",
        "TIMEOUT": 300,  # global default
    }
}

CACHE_TTL = 60 * 5  # 5 minutos

# ============================
# 🧠 DATABASE PERFORMANCE TUNING
# ============================

DATABASES["default"]["CONN_MAX_AGE"] = 60
DATABASES["Evaluacion"]["CONN_MAX_AGE"] = 60

# ============================
# ⚡ CELERY HARDENED (PROD)
# ============================

CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240

CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TRACK_STARTED = True

# ============================
# 📦 STATIC FILES
# ============================

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

WHITENOISE_MAX_AGE = 31536000  # 1 año cache navegador

# ============================
# 📡 LOGGING (PROD STRUCTURED)
# ============================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s'
        },
        'json': {
            'format': '{"level":"%(levelname)s","time":"%(asctime)s","logger":"%(name)s","message":"%(message)s"}'
        },
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },

        'asignaciones_file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/asignaciones.log'),
            'formatter': 'json',
        },
    },

    'loggers': {
        'asignaciones': {
            'handlers': ['console', 'asignaciones_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },

    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# ============================
# 🌐 API / DRF HARDENING
# ============================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),

    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),

    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
}

# ============================
# 📍 MAPS / CACHE EXTRA
# ============================

MAP_CACHE_TTL = 60 * 5
MAP_REDIS_PREFIX = "visor_maps"
MAP_DEFAULT_RADIO = 1000