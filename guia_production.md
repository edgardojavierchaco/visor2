echo 'corriendo collectstatic...'
python3 manage.py collectstatic --no-input --settings=config.settings.production

python3 manage.py migrate --settings=config.settings.production

gunicorn --env DJANGO_SETTINGS_MODULE=config.settings.production config.wsgi:application --bind 0.0.0.0:5000

