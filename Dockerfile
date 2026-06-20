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

# Collect static files at BUILD time, not on every container restart -
# they never change at runtime, so there's no reason to redo this work
# (and risk it failing) every time the container starts.
#
# DJANGO_DEBUG=0 here specifically (separate from whatever Railway sets
# at runtime) because collectstatic needs to run in production mode to
# generate the compressed/manifest static files WhiteNoise serves in
# production - at build time there's no runtime env var yet to tell it
# that, so it must be set explicitly for this step.
ENV DJANGO_DEBUG=0
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn slotting_django.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1"]
