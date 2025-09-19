import os
from pathlib import Path
import environ

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
)

BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = env("SECRET_KEY", default="fake_secret_key_switch_me_123451231")
DEBUG = env("DEBUG", False)
CELERY_TASK_ALWAYS_EAGER = DEBUG
CELERY_TASK_EAGER_PROPAGATES = DEBUG

if not DEBUG:
    sentry_sdk.init(
    dsn=env("SENTRY_DSN"),
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    integrations=[
        CeleryIntegration(
            monitor_beat_tasks=True,
        ),
        DjangoIntegration(),
    ],
)

ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1", "actionsuptime-web.spindlers.dev", "www.actionsuptime.com", "actionsuptime.com"]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.sites",
    # Third-party
    "allauth",
    "allauth.account",
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    "crispy_forms",
    "crispy_bootstrap5",
    "debug_toolbar",
    "django_celery_beat",
    "django_extensions",
    "djstripe",
    # Local
    "accounts",
    "pages",
    "actions",
    "utils",
    "web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "accounts.middleware.SubscriptionMetadataMiddleware",
]

MESSAGE_STORAGE = "django.contrib.messages.storage.fallback.FallbackStorage"

DATABASES = {"default": env.db()}

if os.environ.get('GITHUB_ACTIONS'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": env("REDIS_URL"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            "KEY_PREFIX": "actionsuptime",
        }
    }

# Celery
CELERY_BROKER_URL = env("REDIS_URL")

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

LOCALE_PATHS = [BASE_DIR / 'locale']

STATIC_ROOT = BASE_DIR / "staticfiles"

STATIC_URL = "/static/"

STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = "bootstrap5"


BASE_URL = "https://actionsuptime.com"

INTERNAL_IPS = ["127.0.0.1"]

AUTH_USER_MODEL = "accounts.CustomUser"

SITE_ID = 1

LOGIN_REDIRECT_URL = "home"

ACCOUNT_LOGOUT_REDIRECT_URL = "home"

CSRF_TRUSTED_ORIGINS = ["https://actionsuptime.com", "https://*.spindlers.dev", "https://www.actionsuptime.com"]


AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGOUT_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_STORE_TOKENS = True

SOCIALACCOUNT_PROVIDERS = {
    'github': {
        "SCOPE": ["repo"],
        "APP": {
            "client_id": env("GITHUB_CLIENT_ID"),
            "secret": env("GITHUB_CLIENT_SECRET"),
            "key": "",
        },
        "VERIFIED_EMAIL": True,
    }
}

# SES
EMAIL_BACKEND = "django_ses.SESBackend"
DEFAULT_FROM_EMAIL = '"ActionsUptime" <no-reply@actionsuptime.com>'
SERVER_EMAIL = "no-reply@actionsuptime.com"
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
USE_SES_V2 = True

# Stripe
STRIPE_LIVE_MODE = True
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

# Testing
import sys
TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

DATA_UPLOAD_MAX_NUMBER_FIELDS = 50000