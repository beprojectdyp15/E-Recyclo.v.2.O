web: python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
release: python manage.py migrate --noinput --settings=config.settings.production