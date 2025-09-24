"""
Test-specific settings for running tests in Docker with LocalStack.

This settings file extends the base settings and overrides configurations
for testing with mocked AWS services and test databases.
"""

import os
from .settings import *  # noqa: F403, F401

# Override debug setting for tests
DEBUG = True
TESTING = True

# Test database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'test_aaronspindler'),
        'USER': os.environ.get('POSTGRES_USER', 'test_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'test_password'),
        'HOST': os.environ.get('POSTGRES_HOST', 'postgres'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'TEST': {
            'NAME': 'test_aaronspindler_test',
        }
    }
}

# Redis configuration for testing
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')

# Cache configuration for testing
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'test',
        'TIMEOUT': 300,
    }
}

# Celery configuration for testing
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/1')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/2')
CELERY_TASK_ALWAYS_EAGER = False  # Set to False to test actual async behavior
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# LocalStack S3 configuration
USE_LOCALSTACK = os.environ.get('USE_LOCALSTACK', 'true').lower() == 'true'

if USE_LOCALSTACK:
    # LocalStack endpoint configuration
    AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', 'http://localstack:4566')
    AWS_S3_USE_SSL = os.environ.get('AWS_S3_USE_SSL', 'false').lower() == 'true'
    AWS_S3_VERIFY = False  # Don't verify SSL certificates for LocalStack
    
    # Override AWS settings for LocalStack
    AWS_ACCESS_KEY_ID = 'test'
    AWS_SECRET_ACCESS_KEY = 'test'
    AWS_STORAGE_BUCKET_NAME = 'test-bucket'
    AWS_S3_REGION_NAME = 'us-east-1'
    
    # Update domain to use LocalStack endpoint
    AWS_S3_CUSTOM_DOMAIN = None  # Don't use custom domain for LocalStack
    
    # Storage backends with LocalStack support
    STORAGES = {
        "default": {
            "BACKEND": "config.storage_backends_test.TestPublicMediaStorage",
        },
        "staticfiles": {
            "BACKEND": "config.storage_backends_test.TestStaticStorage",
        },
    }
    
    # Update URLs to use LocalStack endpoint
    MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/public/media/'
    STATIC_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/public/static/'
else:
    # Fall back to file system storage for tests without LocalStack
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    MEDIA_ROOT = os.path.join(BASE_DIR, 'test_media')  # noqa: F405
    MEDIA_URL = '/media/'
    STATIC_ROOT = os.path.join(BASE_DIR, 'test_static')  # noqa: F405
    STATIC_URL = '/static/'

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable security features for testing
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Allow all hosts for testing
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = ['http://localhost:8001', 'http://web:8000', 'http://127.0.0.1:8001']

# Logging configuration for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[TEST] {levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[TEST] {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # Set to DEBUG to see SQL queries
            'propagate': False,
        },
        'boto3': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'botocore': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'urllib3': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Test-specific password hashers (faster for tests)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',  # Fast hasher for tests
]

# Disable migrations for faster test runs (optional)
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# MIGRATION_MODULES = DisableMigrations()

# File upload settings for tests
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB

# Playwright settings for tests
PLAYWRIGHT_BROWSER = 'chromium'
PLAYWRIGHT_HEADLESS = True

# Site framework
SITE_ID = 1

# Disable rate limiting for tests
USE_RATE_LIMITING = False

# Test runner configuration
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
TEST_OUTPUT_DIR = os.path.join(BASE_DIR, 'test_output')  # noqa: F405

# Create test output directory if it doesn't exist
os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
