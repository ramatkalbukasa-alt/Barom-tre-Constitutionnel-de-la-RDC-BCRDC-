from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    OTP_EXPIRY_MINUTES=(int, 10),
    OTP_MAX_ATTEMPTS=(int, 3),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

DJANGO_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.users",
    "apps.constitution",
    "apps.consultation",
    "apps.ai_engine",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL is required (the app relies on django.contrib.postgres features:
# full-text search vectors, GIN indexes, JSON aggregation). No SQLite fallback.
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_USER_MODEL = "users.CitizenUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Kinshasa"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Periodically rebuild the stats snapshot so that AI argument categories
# (computed asynchronously after each vote) are reflected in the dashboard.
CELERY_BEAT_SCHEDULE = {
    "refresh-vote-stats-snapshot": {
        "task": "apps.ai_engine.tasks.refresh_stats_snapshot_task",
        "schedule": 300.0,
    },
}

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_EMBED_MODEL = "text-embedding-3-small"
OPENAI_CHAT_MODEL = "gpt-4o-mini"
OPENAI_TIMEOUT = env.float("OPENAI_TIMEOUT", default=20.0)

# Gemini : fallback gratuit utilise lorsque l'appel OpenAI echoue (quota,
# cle absente, panne reseau). gemini-2.5-flash dispose d'un palier gratuit.
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_CHAT_MODEL = env("GEMINI_CHAT_MODEL", default="gemini-2.5-flash")

OTP_EXPIRY_MINUTES = env("OTP_EXPIRY_MINUTES")
OTP_MAX_ATTEMPTS = env("OTP_MAX_ATTEMPTS")
OTP_RESEND_COOLDOWN_SECONDS = env.int("OTP_RESEND_COOLDOWN_SECONDS", default=60)

# Server-side pepper for phone-number hashing (HMAC-SHA256). Falls back to
# SECRET_KEY so the app still works if the variable is not set, but a dedicated
# value is strongly recommended in production.
PHONE_HASH_PEPPER = env("PHONE_HASH_PEPPER", default="") or SECRET_KEY

# django-ratelimit
RATELIMIT_USE_CACHE = "default"
RATELIMIT_ENABLE = env.bool("RATELIMIT_ENABLE", default=True)

# SMS : mode mock uniquement. Le code OTP est affiché sur l'interface web de
# vérification, aucun SMS réel n'est envoyé (pas de fournisseur externe).

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

JAZZMIN_SETTINGS = {
    "site_title": "BCRDC Admin",
    "site_header": "Baromètre Constitutionnel RDC",
    "site_brand": "BCRDC",
    "welcome_sign": "Administration — Baromètre Constitutionnel de la RDC",
    "copyright": "BCRDC",
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "users.CitizenUser": "fas fa-users",
        "constitution.ConstitutionArticle": "fas fa-scroll",
        "consultation.Vote": "fas fa-vote-yea",
        "ai_engine.AIQuery": "fas fa-robot",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": False,
    "custom_css": None,
    "custom_js": None,
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
}
