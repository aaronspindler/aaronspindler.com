import os

from .settings import *  # noqa: F403, F401

DEBUG = True
TESTING = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "test_aaronspindler"),
        "USER": os.environ.get("POSTGRES_USER", "test_user"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "test_password"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "TEST": {
            "NAME": "test_aaronspindler_test",
        },
    }
}

if os.environ.get("QUESTDB_URL"):
    # Parse QuestDB connection URL using urllib.parse
    from urllib.parse import urlparse

    questdb_url = urlparse(os.environ.get("QUESTDB_URL"))
    DATABASES["questdb"] = {
        "ENGINE": "config.db_backends.questdb",  # Custom backend that skips version check
        "NAME": questdb_url.path.lstrip("/") or "qdb",
        "USER": questdb_url.username or "admin",
        "PASSWORD": questdb_url.password or "quest",
        "HOST": questdb_url.hostname or "questdb",
        "PORT": questdb_url.port or 8812,
        "CONN_MAX_AGE": 600,  # Keep connections alive for 10 minutes
        "CONN_HEALTH_CHECKS": True,  # Check connection health
        "OPTIONS": {
            "connect_timeout": 10,
            "prepare_threshold": 5,  # Cache prepared statements after 5 uses
            "server_side_binding": False,  # Disable server-side binding for QuestDB compatibility
        },
    }
else:
    DATABASES["questdb"] = DATABASES["default"].copy()
    DATABASES["questdb"]["NAME"] = "test_questdb"  # Use separate database to isolate data

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,  # Don't fail tests if Redis is temporarily unavailable
        },
        "KEY_PREFIX": "test",
        "TIMEOUT": 300,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 86400  # 24 hours

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
CELERY_TASK_ALWAYS_EAGER = False  # Set to False to test actual async behavior
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
MEDIA_ROOT = os.path.join(BASE_DIR, "test_media")  # noqa: F405
MEDIA_URL = "/media/"
STATIC_ROOT = os.path.join(BASE_DIR, "test_static")  # noqa: F405
STATIC_URL = "/static/"

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

TRUSTED_PROXY_IPS = [
    "127.0.0.1",
    "::1",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
]

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8001",
    "http://web:8000",
    "http://127.0.0.1:8001",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[TEST] {levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "[TEST] {levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
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
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",  # Set to DEBUG to see SQL queries
            "propagate": False,
        },
        "boto3": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "botocore": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "urllib3": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",  # Fast hasher for tests
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB

SITE_ID = 1

USE_RATE_LIMITING = False

if os.environ.get("TEST_OUTPUT_DIR"):
    TEST_RUNNER = "xmlrunner.extra.djangotestrunner.XMLTestRunner"
    TEST_OUTPUT_DIR = os.environ.get("TEST_OUTPUT_DIR")
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
else:
    TEST_RUNNER = "django.test.runner.DiscoverRunner"
    TEST_OUTPUT_DIR = os.path.join(BASE_DIR, "test_output")  # noqa: F405
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
