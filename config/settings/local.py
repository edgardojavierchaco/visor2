from os import environ
from .base import *

# Obtener la clave secreta de Django desde las variables de entorno
SECRET_KEY = environ.get('DJANGO_SECRET_KEY', 'default-secret-key')  # Proporciona un valor predeterminado si no se establece

# Configuración de entorno de desarrollo: activar el modo de depuración
DEBUG = True

# Lista de hosts permitidos en entorno de desarrollo
ALLOWED_HOSTS = ['0.0.0.0', 'localhost', '127.0.0.1']

# Configuración de la caché en memoria para el entorno de desarrollo
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': '',
    }
}

# Configuración de la base de datos
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': environ.get('POSTGRES_DB', 'visualizador'),
        'USER': environ.get('POSTGRES_USER', 'visualizador'),
        'PASSWORD': environ.get('POSTGRES_PASSWORD', 'Estadisticas24'),
        'HOST': environ.get('POSTGRES_HOST', 'visoreducativochaco.com.ar'),
        'PORT': environ.get('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            'options': '-c search_path=cenpe,public'
        }
    }
}

# Configuración de Django Debug Toolbar
INSTALLED_APPS += [
    'debug_toolbar',
    'django_extensions',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

DEBUG_TOOLBAR_CONFIG = {
    'DISABLE_PANELS': ['debug_toolbar.panels.redirects.RedirectsPanel'],
    'SHOW_TEMPLATE_CONTEXT': False,
}

# Configuración de IPs internas para Debug Toolbar
INTERNAL_IPS = ['127.0.0.1', '10.0.2.2', '0.0.0.0']
if environ.get('USE_DOCKER') == 'yes':
    import socket
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += ['.'.join(ip.split('.')[:-1] + ['1']) for ip in ips]

# WhiteNoise para manejo de archivos estáticos en desarrollo
INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS
