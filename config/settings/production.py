from .base import *

# Clave secreta
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# Producción: modo de depuración desactivado
DEBUG = False

# Hosts permitidos
ALLOWED_HOSTS = ['0.0.0.0', 'localhost','visoreducativochaco.com.ar','www.visoreducativochaco.com.ar']

# Seguridad HTTPS y cookies
SECURE_SSL_REDIRECT =  os.getenv('DJANGO_SECURE_SSL_REDIRECT', 'True').lower() == 'True'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', 3600))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True') == 'True'
SECURE_HSTS_PRELOAD = os.getenv('DJANGO_SECURE_HSTS_PRELOAD', 'True') == 'True'
SECURE_CONTENT_TYPE_NOSNIFF = os.getenv('DJANGO_SECURE_CONTENT_TYPE_NOSNIFF', 'True') == 'True'
CSRF_TRUSTED_ORIGINS = ['https://visoreducativochaco.com.ar', 'https://www.visoreducativochaco.com.ar']


# WhiteNoise para archivos estáticos
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


