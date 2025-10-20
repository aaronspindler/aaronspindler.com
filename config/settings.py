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
]
CSRF_TRUSTED_ORIGINS = [
    "https://aaronspindler.com",
    "https://*.spindlers.org",
    "https://*.spindlers.dev",
    "https://www.aaronspindler.com",
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
    "allauth",
    "allauth.account",
    "storages",  # AWS S3 storage
    "django_celery_beat",  # Celery Beat scheduler
    "rest_framework",  # Django REST Framework
    "rest_framework.authtoken",  # Token authentication
    "django_filters",  # Filtering for DRF
    "corsheaders",  # CORS headers for API
    "drf_spectacular",  # OpenAPI/Swagger documentation
    # Project apps
    "accounts",
    "pages",
    "blog",
    "photos",
    "utils",
    "feefifofunds",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS middleware (must be before CommonMiddleware)
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

# S3 Storage Configuration
STORAGES = {
    "default": {
        "BACKEND": "config.storage_backends.PublicMediaStorage",
    },
    "staticfiles": {
        "BACKEND": "config.storage_backends.StaticStorage",
    },
}

MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/public/media/"
MEDIA_ROOT = ""  # Not used with S3, but Django might expect it

STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/public/static/"

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

RESUME_ENABLED = env("RESUME_ENABLED", default=True)
RESUME_FILENAME = env("RESUME_FILENAME", default="Aaron_Spindler_Resume_2025.pdf")

# ==============================================================================
# Django REST Framework Configuration
# ==============================================================================

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    # Pagination
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # Filtering
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    # Rendering (browsable API only enabled in DEBUG mode)
    "DEFAULT_RENDERER_CLASSES": (
        ["rest_framework.renderers.JSONRenderer", "rest_framework.renderers.BrowsableAPIRenderer"]
        if DEBUG
        else ["rest_framework.renderers.JSONRenderer"]
    ),
    # Parsing
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    # Versioning
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    # Throttling (rate limiting)
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",  # Anonymous users: 100 requests per hour
        "user": "1000/hour",  # Authenticated users: 1000 requests per hour
    },
    # Schema generation
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Exception handling
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
    # Date/time formatting
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
    "DATE_FORMAT": "%Y-%m-%d",
    "TIME_FORMAT": "%H:%M:%S",
}

# Simple JWT Configuration (for FUND-028)
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
}

# drf-spectacular (OpenAPI/Swagger) Configuration
SPECTACULAR_SETTINGS = {
    "TITLE": "FeeFiFoFunds API",
    "DESCRIPTION": "API for fund tracking, analysis, and comparison",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
    },
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React/Vue local dev
    "http://localhost:8080",  # Alternative frontend port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
]

# Add production origins if not in DEBUG mode
if not DEBUG:
    CORS_ALLOWED_ORIGINS.extend(
        [
            "https://aaronspindler.com",
            "https://www.aaronspindler.com",
        ]
    )

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
