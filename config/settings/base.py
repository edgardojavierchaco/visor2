import os
from pathlib import Path
from dotenv import load_dotenv

# Directorios base y raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR

# Cargar variables de entorno
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
    'django.contrib.gis',   
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
    'apps.supervisores',
    'apps.cuenta_regresiva',
    'apps.superescuela',
    'apps.pof',
    'apps.evaluaciones',
    'apps.unidadgestion',
    'apps.uegp',
    'apps.funcionarios',
    'apps.represlegales',
    'apps.intercultural',
]


INSTALLED_APPS = BASE_APPS + LOCAL_APPS

# Middleware
BASE_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.regacceso.middleware.RegistroAccesoMiddleware',
]

THIRD_MIDDLEWARE = [    
    'corsheaders.middleware.CorsMiddleware',
]

MIDDLEWARE = BASE_MIDDLEWARE + THIRD_MIDDLEWARE

# Autenticación
AUTH_USER_MODEL = 'usuarios.UsuariosVisualizador'
AUTHENTICATION_BACKENDS = [
    'apps.usuarios.backends.CustomAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]

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
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Base de datos
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('POSTGRES_HOST'),
        'PORT': os.environ.get('POSTGRES_PORT'),
        'OPTIONS': {
            'options': '-c search_path=cenpe,public,pof'
        }
    }
}

# Configuración de archivos estáticos
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'productionfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static'),]

# Configuración de archivos de medios (para producción)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'productionfiles/media')
#MEDIA_ROOT = ROOT_DIR / 'apps/media'

# Configuración de tiempo y formato
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_L10N = True
USE_TZ = True
DATE_INPUT_FORMATS = ['%d/%m/%Y']

LOGIN_REDIRECT_URL='dash:portada'

# Configuración de CORS y REST Framework
CORS_URLS_REGEX = r'^/api/.*'
CORS_ORIGIN_ALLOW_ALL = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.AllowAny',),
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
}

ROOT_URLCONF='config.urls'

# Configuración de Leaflet
LEAFLET_CONFIG = {
    "DEFAULT_CENTER": (-26.270826, -60.604297),
    "DEFAULT_ZOOM": 6,
}

# Configuración de seguridad
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# URL de Django Admin
ADMIN_URL = 'admin/'

# Configuración de correo electrónico
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

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