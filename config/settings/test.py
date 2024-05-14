from .base import *

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

TEST_RUNNER = 'django.test.runner.DiscoverRunner'
