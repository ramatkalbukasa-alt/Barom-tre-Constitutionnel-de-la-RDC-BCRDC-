from .base import *  # noqa

DEBUG = True

ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:50867",
    "http://localhost:50867",
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "bcrdc-dev",
    }
}

INTERNAL_IPS = ["127.0.0.1"]

try:
    import django_extensions  # noqa
    INSTALLED_APPS += ["django_extensions"]
except ImportError:
    pass
