from os import environ
from .base import *

# Obtener la clave secreta de Django desde las variables de entorno
SECRET_KEY = environ.get('DJANGO_SECRET_KEY')

# Configuración de entorno de desarrollo: activar el modo de depuración
DEBUG = True

# Lista de hosts permitidos en entorno de desarrollo
ALLOWED_HOSTS = ['0.0.0.0', 'localhost', '127.0.0.1']

# Configuración de la caché en memoria para el entorno de desarrollo
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': '',  # Ubicación de la caché en memoria
    }
}



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'visualizador',
        'USER': 'visualizador',
        'PASSWORD': 'Estadisticas24',
        'HOST': 'sigechaco.com.ar',
        'PORT': '5432',
    }
}

INSTALLED_APPS += ['debug_toolbar']  # noqa F405
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']  # noqa F405
DEBUG_TOOLBAR_CONFIG = {
    'DISABLE_PANELS': ['debug_toolbar.panels.redirects.RedirectsPanel'],
    'SHOW_TEMPLATE_CONTEXT': True,
}

INTERNAL_IPS = ['127.0.0.1', '10.0.2.2','0.0.0.0']
if os.environ.get('USE_DOCKER') == 'yes':
    import socket

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += ['.'.join(ip.split('.')[:-1] + ['1']) for ip in ips]

INSTALLED_APPS += ['django_extensions']  # noqa F405
