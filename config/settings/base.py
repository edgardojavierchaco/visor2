import os
from dotenv import load_dotenv
from pathlib import Path

# Directorios base y raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Cargar variables de entorno desde el archivo .env
load_dotenv(Path.joinpath(BASE_DIR, '.env'))

# Directorio de aplicaciones
APPS_DIR = ROOT_DIR / 'apps'

# Configuración de aplicaciones
BASE_APPS =[ 
    #'channels',      
    #'daphne',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',  
    'widget_tweaks',   
    
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
    'apps.oplectura',
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
]

THIRD_MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

MIDDLEWARE = BASE_MIDDLEWARE + THIRD_MIDDLEWARE

AUTH_USER_MODEL = 'usuarios.UsuariosVisualizador'

AUTHENTICATION_BACKENDS = [
    'apps.usuarios.backends.CustomAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
    
]
ROOT_URLCONF = 'config.urls'

# Configuración de plantillas
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR, 'templates'],
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

LOGIN_REDIRECT_URL = '/portada/'  # Ajusta esto según la estructura de tu proyecto

# Configuración de internacionalización y zona horaria
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_L10N = True
USE_TZ = True
SITE_ID = 1  # Indicar que es el sitio principal
LOCALE_PATHS = [str(BASE_DIR / 'locale')]

# Configuración de archivos estáticos y multimedia
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

MEDIA_ROOT = os.path.join(APPS_DIR, 'media')
MEDIA_URL = 'media/'

# Configuración de migraciones
MIGRATION_MODULES = {'sites': 'apps.contrib.sites.migrations'}

# Configuración de log
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s '
            '%(process)d %(thread)d %(message)s'
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

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.AllowAny',),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'visualizadorChaco API',
    'DESCRIPTION': 'Documentation of API endpoints of visualizador',
    'VERSION': '1.0.0',
    'SERVE_PERMISSIONS': ["rest_framework.permissions.IsAdminUser"],
    'SERVERS': [
        {'url': 'http://127.0.0.1:8000', 'description': 'Local Development server'},
        {'url': 'https://relevamientoanual.com.ar', 'description': 'Production server'},
    ],
}


WSGI_APPLICATION = 'config.wsgi.application'

""" CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('redis', 6379)],
        },
    },
} """

X_FRAME_OPTIONS = 'SAMEORIGIN'