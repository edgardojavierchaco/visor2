import os
from dotenv import load_dotenv
from pathlib import Path

# Directorios base y raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR

# Cargar variables de entorno desde el archivo .env
load_dotenv(BASE_DIR / '.env')

# Directorio de aplicaciones
APPS_DIR = ROOT_DIR / 'apps'

# Configuración de aplicaciones
BASE_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'widget_tweaks',
    'django_select2',
    'django.forms',
]

LOCAL_APPS = [
    'apps.mapas',
    'apps.reportes',
    'apps.core',
    'apps.videoteca',
    'apps.usuarios',
    'apps.login',
    'apps.establecimientos',
    'apps.dashboard',
    'apps.archivar',
    'apps.mapoteca',
    'apps.normativa',
    'apps.docentes',
    'apps.alumnos',
    'apps.directores',
    'apps.regacceso',
    'apps.lectocomp',
    'apps.indicadores',
    'apps.asistendoc',
    'apps.cenpe',
    'apps.oplectura',
    'apps.aplicadores',
    'apps.supervisores',
    'apps.cuenta_regresiva',
    'apps.Dm',
]


INSTALLED_APPS = BASE_APPS + LOCAL_APPS

# Configuración de middleware
BASE_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.common.BrokenLinkEmailsMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.regacceso.middleware.RegistroAccesoMiddleware',
]

THIRD_MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

MIDDLEWARE = BASE_MIDDLEWARE + THIRD_MIDDLEWARE

# Configuración de autenticación
AUTH_USER_MODEL = 'usuarios.UsuariosVisualizador'
AUTHENTICATION_BACKENDS = [
    'apps.usuarios.backends.CustomAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# URL raíz de la configuración del proyecto
ROOT_URLCONF = 'config.urls'

# Configuración de plantillas
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# URL de redirección al iniciar sesión
LOGIN_REDIRECT_URL = '/portada/'

# Configuración de internacionalización y zona horaria
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_L10N = True
USE_TZ = True
DATE_INPUT_FORMATS = ['%d/%m/%Y']

# Configuración de archivos estáticos y multimedia
STATIC_ROOT=str(BASE_DIR / 'staticfiles')
STATIC_URL = '/static/'
STATICFILES_DIRS = [str(BASE_DIR / 'static')]
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

MEDIA_ROOT = str(BASE_DIR / 'apps/media')
MEDIA_URL = 'apps/media/'


# Configuración de migraciones
MIGRATION_MODULES = {'sites': 'apps.contrib.sites.migrations'}

# Configuración de logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        }
    },
    'root': {'level': 'INFO', 'handlers': ['console']},
}

# Configuración de CORS
CORS_URLS_REGEX = r'^/api/.*'
CORS_ORIGIN_ALLOW_ALL = True

# Configuración de Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.AllowAny',),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
}

# Configuración de drf-spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'Visualizador Chaco API',
    'DESCRIPTION': 'Documentation of API endpoints of Visualizador Chaco',
    'VERSION': '1.0.0',
    'SERVE_PERMISSIONS': ["rest_framework.permissions.IsAdminUser"],
    'SERVERS': [
        {'url': 'http://127.0.0.1:8000', 'description': 'Local Development server'},
        {'url': 'https://visoreducativochaco.com.ar', 'description': 'Production server'},
    ],
}

# Configuración de Leaflet
LEAFLET_CONFIG = {
    "DEFAULT_CENTER": (-26.270826, -60.604297),
    "DEFAULT_ZOOM": 6,
}

# Configuración de correo electrónico
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

# Configuración de seguridad
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# Django Admin URL
ADMIN_URL = "admin/"

# Configuración de administradores y gerentes
ADMINS = [("Edgardo Javier Gómez", "edgardojavierchaco@gmail.com")]
MANAGERS = ADMINS

# Constante general de inicio centro mapa, lo usa django-leaflet
LEAFLET_CONFIG = {
    "DEFAULT_CENTER": (-26.270826, -60.604297),
    "DEFAULT_ZOOM": 6,
}
