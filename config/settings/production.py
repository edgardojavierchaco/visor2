from .base import *

# Clave secreta
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# Producción: modo de depuración desactivado
DEBUG = False

# Hosts permitidos
ALLOWED_HOSTS = ['0.0.0.0', 'visoreducativochaco.com.ar','www.visoreducativochaco.com.ar']

# Base de datos
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'default_db'),
        'USER': os.getenv('POSTGRES_USER', 'default_user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'default_password'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': '5432',
    }
}

# Seguridad HTTPS y cookies
SECURE_SSL_REDIRECT =  False #os.getenv('DJANGO_SECURE_SSL_REDIRECT', 'True').lower() == 'True'
SESSION_COOKIE_SECURE = False #True
CSRF_COOKIE_SECURE = False #True
SECURE_HSTS_SECONDS = 0 #int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', 3600))
SECURE_HSTS_INCLUDE_SUBDOMAINS = False #os.getenv('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True') == 'True'
SECURE_HSTS_PRELOAD = False #os.getenv('DJANGO_SECURE_HSTS_PRELOAD', 'True') == 'True'
SECURE_CONTENT_TYPE_NOSNIFF = False #os.getenv('DJANGO_SECURE_CONTENT_TYPE_NOSNIFF', 'True') == 'True'

# WhiteNoise para archivos estáticos
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


