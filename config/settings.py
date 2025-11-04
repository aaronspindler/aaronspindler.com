import os
from pathlib import Path

import environ

env = environ.Env(
    DEBUG=(bool, False),
)

BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = env("SECRET_KEY", default="fake_secret_key_switch_me_123451231")
DEBUG = env("DEBUG", False)

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "aaronspindler-web.spindlers.org",
    "aaronspindler-web.spindlers.dev",
    "aaronspindler.com",
    "www.aaronspindler.com",
    "omas.coffee",
    "www.omas.coffee",
]
CSRF_TRUSTED_ORIGINS = [
    "https://aaronspindler.com",
    "https://*.spindlers.org",
    "https://*.spindlers.dev",
    "https://www.aaronspindler.com",
    "https://omas.coffee",
    "https://www.omas.coffee",
]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "django.contrib.postgres",  # PostgreSQL full-text search
    # Third-party apps
    "polymorphic",  # Django polymorphic models
    "allauth",
    "allauth.account",
    "storages",  # AWS S3 storage
    "django_celery_beat",  # Celery Beat scheduler
    # Project apps
    "accounts",
    "pages",
    "blog",
    "photos",
    "utils",
    "feefifofunds",
    "omas",  # Omas Coffee website
]

MIDDLEWARE = [
    "config.domain_routing.DomainRoutingMiddleware",  # Domain-based URL routing (must be first)
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Serve static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "utils.middleware.RequestFingerprintMiddleware",  # Track request fingerprints
]

MESSAGE_STORAGE = "django.contrib.messages.storage.fallback.FallbackStorage"

# Message tags configuration for CSS classes
from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: "debug",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error danger",  # Include both 'error' and 'danger' for compatibility
}

DATABASES = {"default": env.db(default="sqlite:///db.sqlite3")}

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

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
                "pages.context_processors.resume_context",  # Custom context processor for resume settings
                "utils.context_processors.lighthouse_badge",  # Lighthouse badge visibility
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_ROOT = BASE_DIR / "staticfiles"


STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = "root@localhost"

INTERNAL_IPS = ["127.0.0.1", "localhost"]

AUTH_USER_MODEL = "accounts.CustomUser"

SITE_ID = 1

LOGIN_REDIRECT_URL = "home"

ACCOUNT_LOGOUT_REDIRECT_URL = "home"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_UNIQUE_EMAIL = True
# Disable signup/registration
ACCOUNT_ALLOW_REGISTRATION = False
ACCOUNT_ADAPTER = "accounts.adapters.NoSignupAccountAdapter"

# AWS S3 Configuration
# Use fake values for testing when AWS credentials are not set
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="fake-access-key-id")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="fake-secret-access-key")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="test-bucket")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
AWS_DEFAULT_ACL = "public-read"
AWS_S3_VERIFY = True
AWS_S3_FILE_OVERWRITE = True
# Allow CORS for fonts and other assets
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
    "ACL": "public-read",
}
# Ensure proper content types for fonts
AWS_S3_MIME_TYPES = {
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".eot": "application/vnd.ms-fontobject",
}

# Storage Configuration
# Static files: Served by WhiteNoise from container
# Media files: Stored in S3 (photos, user uploads)
STORAGES = {
    "default": {
        "BACKEND": "config.storage_backends.PublicMediaStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/public/media/"
MEDIA_ROOT = ""  # Not used with S3, but Django might expect it

STATIC_URL = "/static/"

# WhiteNoise Configuration
WHITENOISE_MAX_AGE = 31536000  # 1 year cache for static files with versioned names
WHITENOISE_MANIFEST_STRICT = False  # Allow missing files in development
WHITENOISE_KEEP_ONLY_HASHED_FILES = True  # Remove unhashed files to save space


# Performance optimizations
def _whitenoise_immutable_file_test(path, url):
    """Add immutable cache headers for all static files except HTML"""
    return url.startswith("/static/") and not url.endswith((".html", ".htm"))


WHITENOISE_IMMUTABLE_FILE_TEST = _whitenoise_immutable_file_test
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = (
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "zip",
    "gz",
    "tgz",
    "bz2",
    "tbz",
    "xz",
    "br",
    "swf",
    "flv",
    "woff",
    "woff2",
)  # Skip compression for already-compressed files
WHITENOISE_MIMETYPES = {
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}  # Explicitly set mimetypes for better browser caching

if not DEBUG:
    # Security Headers
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"

    CSP_DEFAULT_SRC = ("'self'",)
    CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.cdnfonts.com")
    CSP_SCRIPT_SRC = (
        "'self'",
        "'unsafe-inline'",
        "https://d3js.org",
        "https://cdnjs.cloudflare.com",
    )
    CSP_FONT_SRC = ("'self'", "https://fonts.cdnfonts.com")
    CSP_IMG_SRC = ("'self'", "data:", "https:")
    CSP_CONNECT_SRC = ("'self'",)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} [{name}] {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "stream": "ext://sys.stdout",  # Ensure it goes to stdout for CapRover
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "pages": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "blog": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Redis URL format: redis://username:password@host:port/db_number
REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/1")
USE_DEV_CACHE_PREFIX = env("USE_DEV_CACHE_PREFIX", default=False)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS": True,  # Fall back gracefully if Redis is down
        },
        "KEY_PREFIX": "aaronspindler:dev_" if USE_DEV_CACHE_PREFIX else "aaronspindler",
        "TIMEOUT": 300,  # Default cache timeout of 5 minutes
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400  # 24 hours

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_WORKER_POOL_RESTARTS = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Task result and log retention settings
# Store extended task metadata including return values, exceptions, and tracebacks
CELERY_RESULT_EXTENDED = True
# Keep task results for 90 days (7776000 seconds)
CELERY_RESULT_EXPIRES = 7776000
# Send task events for monitoring (enables Flower to track task progress)
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

RESUME_ENABLED = env("RESUME_ENABLED", default=True)
RESUME_FILENAME = env("RESUME_FILENAME", default="Aaron_Spindler_Resume_2025.pdf")

MASSIVE_API_KEY = env("MASSIVE_API_KEY", default="")
