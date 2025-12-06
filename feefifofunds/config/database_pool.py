"""
Connection pooling configuration for FeeFiFoFunds databases.

This module provides optimized connection pooling settings for both PostgreSQL
and QuestDB, including connection management, health checks, and performance tuning.
"""

from typing import Any, Dict

from django.conf import settings


class DatabasePoolConfig:
    """
    Centralized database connection pooling configuration.

    Provides optimized settings for connection pooling, health checks,
    and performance tuning for different database backends.
    """

    # Default PostgreSQL connection pool settings
    POSTGRES_POOL_CONFIG = {
        # Connection pool settings
        "CONN_MAX_AGE": 600,  # Keep connections alive for 10 minutes
        "CONN_HEALTH_CHECKS": True,  # Enable connection health checks
        "OPTIONS": {
            # Connection timeout in seconds
            "connect_timeout": 10,
            # Statement timeout in milliseconds (30 seconds)
            "statement_timeout": 30000,
            # Idle transaction timeout in milliseconds (60 seconds)
            "idle_in_transaction_session_timeout": 60000,
            # Connection pool settings for psycopg2
            "options": "-c default_statistics_target=100",
            # Server-side cursors for large result sets
            "server_side_cursors": True,
            # Prepare threshold for statement caching
            "prepare_threshold": 5,
        },
        "POOL": {
            # Min/max pool size
            "MIN_SIZE": 2,
            "MAX_SIZE": 20,
            # Max overflow connections beyond pool_size
            "MAX_OVERFLOW": 10,
            # Number of seconds to wait before timing out
            "POOL_TIMEOUT": 30,
            # Recycle connections after this many seconds
            "POOL_RECYCLE": 3600,  # 1 hour
            # Number of seconds between keepalive pings
            "POOL_PRE_PING": True,
            # Reset connection state on return to pool
            "POOL_RESET_ON_RETURN": "rollback",
        },
    }

    # Optimized QuestDB connection pool settings
    QUESTDB_POOL_CONFIG = {
        # Connection pool settings
        "CONN_MAX_AGE": 1800,  # Keep connections alive for 30 minutes (longer for time-series)
        "CONN_HEALTH_CHECKS": True,  # Enable connection health checks
        "OPTIONS": {
            # Connection timeout in seconds
            "connect_timeout": 10,
            # QuestDB-specific optimizations
            "prepare_threshold": 5,  # Cache prepared statements after 5 uses
            "server_side_binding": True,  # Use server-side parameter binding
            # Buffer size for bulk operations
            "array_size": 10000,  # Fetch this many rows at a time
            # Write buffer for bulk inserts
            "batch_size": 5000,  # Batch inserts for better performance
            # Statement timeout (60 seconds for complex time-series queries)
            "statement_timeout": 60000,
        },
        "POOL": {
            # Min/max pool size (higher for time-series workloads)
            "MIN_SIZE": 5,
            "MAX_SIZE": 50,
            # Max overflow connections
            "MAX_OVERFLOW": 25,
            # Connection timeout
            "POOL_TIMEOUT": 30,
            # Recycle connections more frequently for QuestDB
            "POOL_RECYCLE": 1800,  # 30 minutes
            # Keepalive
            "POOL_PRE_PING": True,
            # Don't reset on return (QuestDB handles this)
            "POOL_RESET_ON_RETURN": None,
        },
    }

    # Redis connection pool settings (for cache and Celery)
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
        """
        Get optimized PostgreSQL configuration with connection pooling.

        Args:
            database_name: Name of the database configuration

        Returns:
            Dictionary with database configuration including pooling
        """
        base_config = settings.DATABASES.get(database_name, {}).copy()

        # Merge with optimized pool config
        base_config.update(cls.POSTGRES_POOL_CONFIG)

        # Merge OPTIONS carefully
        base_options = base_config.get("OPTIONS", {})
        base_options.update(cls.POSTGRES_POOL_CONFIG["OPTIONS"])
        base_config["OPTIONS"] = base_options

        return base_config

    @classmethod
    def get_questdb_config(cls) -> Dict[str, Any]:
        """
        Get optimized QuestDB configuration with connection pooling.

        Returns:
            Dictionary with QuestDB configuration including pooling
        """
        base_config = settings.DATABASES.get("questdb", {}).copy()

        # Merge with optimized pool config
        base_config.update(cls.QUESTDB_POOL_CONFIG)

        # Merge OPTIONS carefully
        base_options = base_config.get("OPTIONS", {})
        base_options.update(cls.QUESTDB_POOL_CONFIG["OPTIONS"])
        base_config["OPTIONS"] = base_options

        return base_config

    @classmethod
    def get_redis_config(cls) -> Dict[str, Any]:
        """
        Get optimized Redis configuration with connection pooling.

        Returns:
            Dictionary with Redis configuration including pooling
        """
        base_config = settings.CACHES.get("default", {}).get("OPTIONS", {}).copy()

        # Merge with optimized pool config
        base_config.update(cls.REDIS_POOL_CONFIG)

        # Merge CONNECTION_POOL_KWARGS carefully
        base_pool_kwargs = base_config.get("CONNECTION_POOL_KWARGS", {})
        base_pool_kwargs.update(cls.REDIS_POOL_CONFIG["CONNECTION_POOL_KWARGS"])
        base_config["CONNECTION_POOL_KWARGS"] = base_pool_kwargs

        return base_config

    @classmethod
    def apply_pooling_to_settings(cls):
        """
        Apply optimized pooling configuration to Django settings.

        This should be called in settings.py after database configuration.
        """
        # Apply to default database if it's PostgreSQL
        if "default" in settings.DATABASES:
            db_engine = settings.DATABASES["default"].get("ENGINE", "")
            if "postgresql" in db_engine or "psycopg" in db_engine:
                settings.DATABASES["default"] = cls.get_postgres_config("default")

        # Apply to QuestDB
        if "questdb" in settings.DATABASES:
            settings.DATABASES["questdb"] = cls.get_questdb_config()

        # Apply to Redis cache
        if "default" in settings.CACHES:
            cache_config = settings.CACHES["default"]
            if "redis" in cache_config.get("BACKEND", "").lower():
                cache_config["OPTIONS"] = cls.get_redis_config()
                settings.CACHES["default"] = cache_config


# Connection pool manager for runtime management
class ConnectionPoolManager:
    """
    Runtime connection pool management and monitoring.

    Provides utilities for monitoring pool health, adjusting pool sizes,
    and collecting pool metrics.
    """

    @staticmethod
    def get_pool_stats(connection_alias: str = "default") -> Dict[str, Any]:
        """
        Get current connection pool statistics.

        Args:
            connection_alias: Database alias from settings

        Returns:
            Dictionary with pool statistics
        """
        from django.db import connections

        connection = connections[connection_alias]
        stats = {
            "alias": connection_alias,
            "vendor": connection.vendor,
            "is_usable": connection.is_usable(),
        }

        # Try to get pool-specific stats if available
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
        """
        Reset/recreate the connection pool for a database.

        Args:
            connection_alias: Database alias from settings
        """
        from django.db import connections

        connections[connection_alias].close()
        # Connection will be recreated on next use

    @staticmethod
    def warm_connection_pool(connection_alias: str = "default", num_connections: int = 5):
        """
        Pre-warm connection pool by establishing connections.

        Args:
            connection_alias: Database alias from settings
            num_connections: Number of connections to pre-establish
        """
        from django.db import connections

        for _ in range(num_connections):
            conn = connections[connection_alias]
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")

    @staticmethod
    def monitor_pool_health(connection_alias: str = "default") -> bool:
        """
        Check if connection pool is healthy.

        Args:
            connection_alias: Database alias from settings

        Returns:
            True if pool is healthy, False otherwise
        """
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


# Export for easy import
__all__ = ["DatabasePoolConfig", "ConnectionPoolManager"]
