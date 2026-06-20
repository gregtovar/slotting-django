"""
Django settings for the Slotting Optimizer web UI.

This app stores its real data in data/*.csv via app/data_manager.py -
not in Django's database. The DATABASES setting below exists only
because Django's session/messages/auth frameworks expect one; no
migrations from this app touch it. Run `python manage.py migrate` once
to create the (tiny, otherwise-unused) sqlite file Django needs for
sessions to work.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security -----------------------------------------------------------
# For real deployment, set DJANGO_SECRET_KEY and DJANGO_DEBUG=0 as
# environment variables rather than relying on these defaults.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-insecure-secret-key-change-this-before-deploying",
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

# --- Apps / middleware ----------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "slotting",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "slotting_django.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "slotting.context_processors.nav_context",
            ],
        },
    },
]

WSGI_APPLICATION = "slotting_django.wsgi.application"
ASGI_APPLICATION = "slotting_django.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

if DEBUG:
    # Plain storage in dev/tests - no collectstatic run yet, and none needed
    STORAGES = {
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    # Compressed + manifest storage in production - the Procfile always
    # runs `collectstatic` before starting gunicorn, so the manifest
    # this backend needs is guaranteed to exist by the time a request
    # actually arrives.
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Result/CSV exports can get large (e.g. Orders has thousands of rows) -
# raise the default GET param limits a little for the run/export forms.
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000

# --- Reverse-proxy / HTTPS awareness ---------------------------------
# Railway (and most managed platforms) terminate HTTPS at a proxy and
# forward plain HTTP internally, with an X-Forwarded-Proto header saying
# so - without this, Django can't tell the request was actually secure,
# which breaks secure cookies and CSRF checks behind such a proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Set this to your actual deployed domain(s) once you have one, e.g.
# DJANGO_CSRF_TRUSTED_ORIGINS=https://your-app.up.railway.app
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]
