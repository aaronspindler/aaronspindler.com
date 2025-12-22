import hashlib
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CacheManager:
    PREFIX_ASSET = "feefifofunds:asset"
    PREFIX_PRICE = "feefifofunds:price"
    PREFIX_COVERAGE = "feefifofunds:coverage"
    PREFIX_GAP = "feefifofunds:gap"
    PREFIX_METRICS = "feefifofunds:metrics"
    PREFIX_API_RESPONSE = "feefifofunds:api"

    TTL_SHORT = 60  # 1 minute for volatile data
    TTL_MEDIUM = 300  # 5 minutes for frequently updated data
    TTL_LONG = 3600  # 1 hour for stable data
    TTL_VERY_LONG = 86400  # 24 hours for static data

    TTL_CONFIG = {
        "asset_metadata": TTL_VERY_LONG,  # Asset info rarely changes
        "price_recent": TTL_SHORT,  # Recent prices update frequently
        "price_historical": TTL_LONG,  # Historical prices are stable
        "coverage_range": TTL_MEDIUM,  # Coverage updates during ingestion
        "gap_status": TTL_MEDIUM,  # Gap status changes during backfill
        "completeness_metrics": TTL_LONG,  # Metrics update periodically
        "api_response": TTL_MEDIUM,  # API responses for rate limiting
    }

    @classmethod
    def _make_key(cls, prefix: str, *args) -> str:
        # Convert arguments to strings and join
        parts = [str(arg) for arg in args if arg is not None]
        key_suffix = ":".join(parts)

        env_prefix = ""
        if hasattr(settings, "USE_DEV_CACHE_PREFIX") and settings.USE_DEV_CACHE_PREFIX:
            env_prefix = "dev:"

        return f"{env_prefix}{prefix}:{key_suffix}"

    @classmethod
    def _hash_key(cls, key: str) -> str:
        if len(key) > 250:  # Redis key limit is 512MB, but keep it reasonable
            hash_suffix = hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()[:8]
            return f"{key[:240]}:{hash_suffix}"
        return key

    @classmethod
    def get_asset(cls, asset_id: int) -> Optional[Dict[str, Any]]:
        key = cls._make_key(cls.PREFIX_ASSET, asset_id)
        return cache.get(key)

    @classmethod
    def set_asset(cls, asset_id: int, asset_data: Dict[str, Any]):
        key = cls._make_key(cls.PREFIX_ASSET, asset_id)
        cache.set(key, asset_data, timeout=cls.TTL_CONFIG["asset_metadata"])

    @classmethod
    def get_price_data(
        cls,
        asset_id: int,
        interval_minutes: int,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[List[Dict[str, Any]]]:
        key = cls._make_key(
            cls.PREFIX_PRICE,
            asset_id,
            interval_minutes,
            start_date.isoformat(),
            end_date.isoformat(),
        )
        key = cls._hash_key(key)
        return cache.get(key)

    @classmethod
    def set_price_data(
        cls,
        asset_id: int,
        interval_minutes: int,
        start_date: datetime,
        end_date: datetime,
        data: List[Dict[str, Any]],
    ):
        key = cls._make_key(
            cls.PREFIX_PRICE,
            asset_id,
            interval_minutes,
            start_date.isoformat(),
            end_date.isoformat(),
        )
        key = cls._hash_key(key)

        now = datetime.now()
        if end_date > now - timedelta(hours=1):
            ttl = cls.TTL_CONFIG["price_recent"]
        else:
            ttl = cls.TTL_CONFIG["price_historical"]

        cache.set(key, data, timeout=ttl)

    @classmethod
    def get_coverage_ranges(cls, asset_id: int, interval_minutes: int) -> Optional[List[Dict[str, Any]]]:
        key = cls._make_key(cls.PREFIX_COVERAGE, asset_id, interval_minutes)
        return cache.get(key)

    @classmethod
    def set_coverage_ranges(cls, asset_id: int, interval_minutes: int, ranges: List[Dict[str, Any]]):
        key = cls._make_key(cls.PREFIX_COVERAGE, asset_id, interval_minutes)
        cache.set(key, ranges, timeout=cls.TTL_CONFIG["coverage_range"])

    @classmethod
    def invalidate_coverage(cls, asset_id: int, interval_minutes: Optional[int] = None):
        if interval_minutes:
            key = cls._make_key(cls.PREFIX_COVERAGE, asset_id, interval_minutes)
            cache.delete(key)
        else:
            pattern = cls._make_key(cls.PREFIX_COVERAGE, asset_id, "*")
            cache.delete_pattern(pattern)

    @classmethod
    def get_gaps(cls, asset_id: int, interval_minutes: int) -> Optional[List[Dict[str, Any]]]:
        key = cls._make_key(cls.PREFIX_GAP, asset_id, interval_minutes)
        return cache.get(key)

    @classmethod
    def set_gaps(cls, asset_id: int, interval_minutes: int, gaps: List[Dict[str, Any]]):
        key = cls._make_key(cls.PREFIX_GAP, asset_id, interval_minutes)
        cache.set(key, gaps, timeout=cls.TTL_CONFIG["gap_status"])

    @classmethod
    def get_completeness_metrics(cls, tier: str) -> Optional[Dict[str, Any]]:
        key = cls._make_key(cls.PREFIX_METRICS, "completeness", tier)
        return cache.get(key)

    @classmethod
    def set_completeness_metrics(cls, tier: str, metrics: Dict[str, Any]):
        key = cls._make_key(cls.PREFIX_METRICS, "completeness", tier)
        cache.set(key, metrics, timeout=cls.TTL_CONFIG["completeness_metrics"])

    @classmethod
    def get_api_response(cls, endpoint: str, params_hash: str) -> Optional[Any]:
        key = cls._make_key(cls.PREFIX_API_RESPONSE, endpoint, params_hash)
        key = cls._hash_key(key)
        return cache.get(key)

    @classmethod
    def set_api_response(cls, endpoint: str, params_hash: str, response: Any):
        key = cls._make_key(cls.PREFIX_API_RESPONSE, endpoint, params_hash)
        key = cls._hash_key(key)
        cache.set(key, response, timeout=cls.TTL_CONFIG["api_response"])

    @classmethod
    def get_many(cls, keys: List[str]) -> Dict[str, Any]:
        hashed_keys = {cls._hash_key(k): k for k in keys}
        results = cache.get_many(list(hashed_keys.keys()))

        return {hashed_keys[hk]: v for hk, v in results.items()}

    @classmethod
    def set_many(cls, data: Dict[str, Any], timeout: Optional[int] = None):
        hashed_data = {cls._hash_key(k): v for k, v in data.items()}
        cache.set_many(hashed_data, timeout=timeout or cls.TTL_MEDIUM)

    @classmethod
    def delete_many(cls, keys: List[str]):
        hashed_keys = [cls._hash_key(k) for k in keys]
        cache.delete_many(hashed_keys)

    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        try:
            if hasattr(cache, "_cache"):
                client = cache._cache.get_client()
                info = client.info()
                return {
                    "backend": "redis",
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_connections": info.get("total_connections_received"),
                    "keyspace_hits": info.get("keyspace_hits"),
                    "keyspace_misses": info.get("keyspace_misses"),
                    "hit_rate": info.get("keyspace_hits", 0)
                    / (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
                    * 100,
                }
        except Exception as e:
            logger.warning(f"Could not get cache statistics: {e}")

        return {"backend": "unknown", "status": "no statistics available"}

    @classmethod
    def clear_all(cls, prefix: Optional[str] = None):
        if prefix:
            pattern = f"{prefix}:*"
            cache.delete_pattern(pattern)
            logger.info(f"Cleared cache entries matching pattern: {pattern}")
        else:
            cache.clear()
            logger.info("Cleared all cache entries")


def cache_result(
    key_func: Optional[Callable] = None,
    timeout: Optional[int] = None,
    prefix: str = "feefifofunds:func",
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                if args:
                    key_parts.extend(str(arg) for arg in args)
                if kwargs:
                    key_parts.append(json.dumps(kwargs, sort_keys=True))
                cache_key = ":".join(key_parts)

            cache_key = f"{prefix}:{cache_key}"
            cache_key = CacheManager._hash_key(cache_key)

            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result

            result = func(*args, **kwargs)
            cache_timeout = timeout or CacheManager.TTL_MEDIUM
            cache.set(cache_key, result, timeout=cache_timeout)
            logger.debug(f"Cached result for {func.__name__}")

            return result

        # Add cache invalidation method
        def invalidate(*args, **kwargs):
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                if args:
                    key_parts.extend(str(arg) for arg in args)
                if kwargs:
                    key_parts.append(json.dumps(kwargs, sort_keys=True))
                cache_key = ":".join(key_parts)

            cache_key = f"{prefix}:{cache_key}"
            cache_key = CacheManager._hash_key(cache_key)
            cache.delete(cache_key)
            logger.debug(f"Invalidated cache for {func.__name__}")

        wrapper.invalidate = invalidate
        return wrapper

    return decorator


def cache_page_result(timeout: int = 300, vary_on_headers: Optional[List[str]] = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            key_parts = [request.path, request.method]

            if request.GET:
                key_parts.append(request.GET.urlencode())

            if vary_on_headers:
                for header in vary_on_headers:
                    value = request.META.get(header, "")
                    key_parts.append(f"{header}={value}")

            cache_key = CacheManager._make_key("page", *key_parts)
            cache_key = CacheManager._hash_key(cache_key)

            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.debug(f"Page cache hit for {request.path}")
                return cached_response

            response = func(request, *args, **kwargs)

            if response.status_code == 200:
                cache.set(cache_key, response, timeout=timeout)
                logger.debug(f"Cached page response for {request.path}")

            return response

        return wrapper

    return decorator
