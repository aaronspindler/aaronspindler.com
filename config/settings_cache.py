"""
Cache configuration for the photos application.
This module provides Redis-based caching with fallback to local memory cache.
"""
import os

# Cache configuration
CACHE_TTL = 60 * 15  # 15 minutes default cache timeout

# Redis configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('REDIS_DB', 1))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')

# Cache key prefixes
CACHE_KEY_PREFIX = 'photos'
ALBUM_LIST_CACHE_KEY = f'{CACHE_KEY_PREFIX}:album:list'
ALBUM_DETAIL_CACHE_KEY = f'{CACHE_KEY_PREFIX}:album:detail'
PHOTO_CACHE_KEY = f'{CACHE_KEY_PREFIX}:photo'
STATS_CACHE_KEY = f'{CACHE_KEY_PREFIX}:stats'

# Cache timeouts (in seconds)
CACHE_TIMEOUTS = {
    'album_list': 60 * 30,  # 30 minutes
    'album_detail': 60 * 15,  # 15 minutes
    'photo': 60 * 60,  # 1 hour
    'thumbnail': 60 * 60 * 24,  # 24 hours
    'stats': 60 * 5,  # 5 minutes
}

# Configure caches
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{":" + REDIS_PASSWORD + "@" if REDIS_PASSWORD else ""}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,  # Fallback gracefully if Redis is down
        },
        'KEY_PREFIX': CACHE_KEY_PREFIX,
        'TIMEOUT': CACHE_TTL,
    },
    'thumbnails': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{":" + REDIS_PASSWORD + "@" if REDIS_PASSWORD else ""}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB + 1}',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': f'{CACHE_KEY_PREFIX}:thumb',
        'TIMEOUT': 60 * 60 * 24 * 7,  # 7 days for thumbnails
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{":" + REDIS_PASSWORD + "@" if REDIS_PASSWORD else ""}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB + 2}',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'session',
    },
}

# Fallback to local memory cache if Redis is not available
if not os.environ.get('REDIS_HOST'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
            'TIMEOUT': CACHE_TTL,
            'OPTIONS': {
                'MAX_ENTRIES': 1000,
            }
        },
        'thumbnails': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': '/tmp/django_cache/thumbnails',
            'TIMEOUT': 60 * 60 * 24 * 7,
        },
        'sessions': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table',
        }
    }

# Session configuration to use cache
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'