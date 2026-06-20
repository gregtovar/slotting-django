# Plain Django deployment image - no virtual display, no VNC, none of
# the desktop-app machinery in deploy/Dockerfile. Just Python + Django
# + gunicorn, explicitly, so there's no ambiguity for Railway (or any
# other Docker-based host) about what to install or how to start it.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=slotting_django.settings

WORKDIR /app

COPY requirements-django.txt .
RUN pip install --no-cache-dir -r requirements-django.txt

COPY . .

EXPOSE 8000

CMD python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    gunicorn slotting_django.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1
