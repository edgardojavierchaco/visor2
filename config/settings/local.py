from .base import *

# Clave secreta
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'default-secret-key')

# Desarrollo: activación del modo de depuración
DEBUG = True

# Hosts permitidos
ALLOWED_HOSTS = ['0.0.0.0', 'localhost', '127.0.0.1']

# Base de datos
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.getenv('POSTGRES_DB', 'visualizador'),
        'USER': os.getenv('POSTGRES_USER', 'visualizador'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'Estadisticas24'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': '5432',
    }
}

# Caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': '',
    }
}

# Django Debug Toolbar
INSTALLED_APPS += ['debug_toolbar', 'django_extensions']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TEMPLATE_CONTEXT': False,
}

# WhiteNoise para desarrollo
INSTALLED_APPS = ['whitenoise.runserver_nostatic'] + INSTALLED_APPS

# IP internas
INTERNAL_IPS = ['127.0.0.1', '10.0.2.2']
