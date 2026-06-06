from .base import *  # noqa

DEBUG = True

ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CORS_ALLOW_ALL_ORIGINS = True

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
