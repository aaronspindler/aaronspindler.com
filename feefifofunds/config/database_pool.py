from typing import Any, Dict

from django.conf import settings


class DatabasePoolConfig:
    POSTGRES_POOL_CONFIG = {
        "CONN_MAX_AGE": 600,  # Keep connections alive for 10 minutes
        "CONN_HEALTH_CHECKS": True,  # Enable connection health checks
        "OPTIONS": {
            "connect_timeout": 10,
            "statement_timeout": 30000,
            "idle_in_transaction_session_timeout": 60000,
            "options": "-c default_statistics_target=100",
            "server_side_cursors": True,
            "prepare_threshold": 5,
        },
        "POOL": {
            "MIN_SIZE": 2,
            "MAX_SIZE": 20,
            "MAX_OVERFLOW": 10,
            "POOL_TIMEOUT": 30,
            "POOL_RECYCLE": 3600,  # 1 hour
            "POOL_PRE_PING": True,
            "POOL_RESET_ON_RETURN": "rollback",
        },
    }

    QUESTDB_POOL_CONFIG = {
        "CONN_MAX_AGE": 1800,  # Keep connections alive for 30 minutes (longer for time-series)
        "CONN_HEALTH_CHECKS": True,  # Enable connection health checks
        "OPTIONS": {
            "connect_timeout": 10,
            # QuestDB-specific optimizations
            "prepare_threshold": 5,  # Cache prepared statements after 5 uses
            "server_side_binding": True,  # Use server-side parameter binding
            "array_size": 10000,  # Fetch this many rows at a time
            "batch_size": 5000,  # Batch inserts for better performance
            "statement_timeout": 60000,
        },
        "POOL": {
            "MIN_SIZE": 5,
            "MAX_SIZE": 50,
            "MAX_OVERFLOW": 25,
            "POOL_TIMEOUT": 30,
            "POOL_RECYCLE": 1800,  # 30 minutes
            "POOL_PRE_PING": True,
            # Don't reset on return (QuestDB handles this)
            "POOL_RESET_ON_RETURN": None,
        },
    }

    REDIS_POOL_CONFIG = {
        "CONNECTION_POOL_KWARGS": {
            "max_connections": 100,  # Increased for high throughput
            "retry_on_timeout": True,
            "retry_on_error": [ConnectionError, TimeoutError],
            "socket_keepalive": True,
            "socket_keepalive_options": {
                1: 1,  # TCP_KEEPIDLE
                2: 1,  # TCP_KEEPINTVL
                3: 3,  # TCP_KEEPCNT
            },
            "health_check_interval": 30,
        },
        "SOCKET_CONNECT_TIMEOUT": 5,
        "SOCKET_TIMEOUT": 5,
        "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
        "PARSER_CLASS": "redis.connection.HiredisParser",
    }

    @classmethod
    def get_postgres_config(cls, database_name: str = "default") -> Dict[str, Any]:
        base_config = settings.DATABASES.get(database_name, {}).copy()

        base_config.update(cls.POSTGRES_POOL_CONFIG)

        base_options = base_config.get("OPTIONS", {})
        base_options.update(cls.POSTGRES_POOL_CONFIG["OPTIONS"])
        base_config["OPTIONS"] = base_options

        return base_config

    @classmethod
    def get_questdb_config(cls) -> Dict[str, Any]:
        base_config = settings.DATABASES.get("questdb", {}).copy()

        base_config.update(cls.QUESTDB_POOL_CONFIG)

        base_options = base_config.get("OPTIONS", {})
        base_options.update(cls.QUESTDB_POOL_CONFIG["OPTIONS"])
        base_config["OPTIONS"] = base_options

        return base_config

    @classmethod
    def get_redis_config(cls) -> Dict[str, Any]:
        base_config = settings.CACHES.get("default", {}).get("OPTIONS", {}).copy()

        base_config.update(cls.REDIS_POOL_CONFIG)

        base_pool_kwargs = base_config.get("CONNECTION_POOL_KWARGS", {})
        base_pool_kwargs.update(cls.REDIS_POOL_CONFIG["CONNECTION_POOL_KWARGS"])
        base_config["CONNECTION_POOL_KWARGS"] = base_pool_kwargs

        return base_config

    @classmethod
    def apply_pooling_to_settings(cls):
        if "default" in settings.DATABASES:
            db_engine = settings.DATABASES["default"].get("ENGINE", "")
            if "postgresql" in db_engine or "psycopg" in db_engine:
                settings.DATABASES["default"] = cls.get_postgres_config("default")

        if "questdb" in settings.DATABASES:
            settings.DATABASES["questdb"] = cls.get_questdb_config()

        if "default" in settings.CACHES:
            cache_config = settings.CACHES["default"]
            if "redis" in cache_config.get("BACKEND", "").lower():
                cache_config["OPTIONS"] = cls.get_redis_config()
                settings.CACHES["default"] = cache_config


class ConnectionPoolManager:
    @staticmethod
    def get_pool_stats(connection_alias: str = "default") -> Dict[str, Any]:
        from django.db import connections

        connection = connections[connection_alias]
        stats = {
            "alias": connection_alias,
            "vendor": connection.vendor,
            "is_usable": connection.is_usable(),
        }

        if hasattr(connection, "pool"):
            pool = connection.pool
            stats.update(
                {
                    "pool_size": getattr(pool, "size", None),
                    "pool_checked_in": getattr(pool, "checkedin", None),
                    "pool_overflow": getattr(pool, "overflow", None),
                    "pool_total": getattr(pool, "total", None),
                }
            )

        return stats

    @staticmethod
    def reset_connection_pool(connection_alias: str = "default"):
        from django.db import connections

        connections[connection_alias].close()

    @staticmethod
    def warm_connection_pool(connection_alias: str = "default", num_connections: int = 5):
        from django.db import connections

        for _ in range(num_connections):
            conn = connections[connection_alias]
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")

    @staticmethod
    def monitor_pool_health(connection_alias: str = "default") -> bool:
        import logging

        from django.db import connections

        logger = logging.getLogger(__name__)

        try:
            conn = connections[connection_alias]
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    return True
        except Exception as e:
            logger.error(f"Connection pool health check failed for {connection_alias}: {e}")
            return False

        return False


__all__ = ["DatabasePoolConfig", "ConnectionPoolManager"]
