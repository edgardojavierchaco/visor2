from .base import *

# General
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

TEST_RUNNER = 'django.test.runner.DiscoverRunner'


# Password
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Email
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'