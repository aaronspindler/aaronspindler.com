"""
Cache utilities for the photos application.
Provides caching decorators and cache invalidation functions.
"""
import hashlib
import logging
from functools import wraps
from typing import Any, Callable, Optional, Union
from django.core.cache import cache, caches
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.conf import settings
from django.db.models import Model
from django.http import HttpRequest
from django.utils.cache import get_cache_key, patch_cache_control
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

logger = logging.getLogger(__name__)

# Cache timeout configurations
CACHE_TTL = getattr(settings, 'CACHE_TTL', 60 * 15)  # 15 minutes default

CACHE_TIMEOUTS = {
    'album_list': 60 * 30,  # 30 minutes
    'album_detail': 60 * 15,  # 15 minutes
    'photo': 60 * 60,  # 1 hour
    'thumbnail': 60 * 60 * 24,  # 24 hours
    'stats': 60 * 5,  # 5 minutes
    'photo_count': 60 * 10,  # 10 minutes
}


def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a consistent cache key from prefix and arguments.
    
    Args:
        prefix: Cache key prefix
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key
    
    Returns:
        str: Generated cache key
    """
    key_parts = [prefix]
    
    # Add args to key
    for arg in args:
        if isinstance(arg, Model):
            key_parts.append(f"{arg.__class__.__name__}:{arg.pk}")
        else:
            key_parts.append(str(arg))
    
    # Add kwargs to key (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        if isinstance(v, Model):
            key_parts.append(f"{k}={v.__class__.__name__}:{v.pk}")
        else:
            key_parts.append(f"{k}={v}")
    
    # Create hash for long keys
    full_key = ":".join(key_parts)
    if len(full_key) > 200:  # Django's memcached key length limit is 250
        key_hash = hashlib.md5(full_key.encode()).hexdigest()
        return f"{prefix}:hash:{key_hash}"
    
    return full_key


def cache_result(timeout: Optional[int] = None, key_prefix: str = '', 
                 cache_name: str = 'default', vary_on_user: bool = False):
    """
    Decorator to cache function results.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache key
        cache_name: Name of cache to use
        vary_on_user: Whether to vary cache by user
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            if vary_on_user and hasattr(args[0], 'user'):
                user_id = args[0].user.id if args[0].user.is_authenticated else 'anon'
                cache_key = make_cache_key(f"{key_prefix}:{func.__name__}:user:{user_id}", *args[1:], **kwargs)
            else:
                cache_key = make_cache_key(f"{key_prefix}:{func.__name__}", *args, **kwargs)
            
            # Try to get from cache
            cache_backend = caches[cache_name]
            result = cache_backend.get(cache_key)
            
            if result is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for key: {cache_key}")
            result = func(*args, **kwargs)
            
            # Only cache non-None results
            if result is not None:
                cache_timeout = timeout or CACHE_TTL
                cache_backend.set(cache_key, result, cache_timeout)
                logger.debug(f"Cached result for key: {cache_key} (timeout: {cache_timeout}s)")
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str, cache_name: str = 'default'):
    """
    Invalidate all cache keys matching a pattern.
    
    Args:
        pattern: Cache key pattern to match
        cache_name: Name of cache to clear
    """
    try:
        cache_backend = caches[cache_name]
        if hasattr(cache_backend, 'delete_pattern'):
            # Redis backend supports pattern deletion
            deleted = cache_backend.delete_pattern(f"*{pattern}*")
            logger.info(f"Invalidated {deleted} cache keys matching pattern: {pattern}")
        else:
            # Fallback for other backends
            logger.warning(f"Cache backend {cache_name} doesn't support pattern deletion")
    except Exception as e:
        logger.error(f"Error invalidating cache pattern {pattern}: {e}")


def invalidate_album_cache(album_id: Optional[int] = None):
    """
    Invalidate cache for album(s).
    
    Args:
        album_id: Specific album ID to invalidate, or None for all albums
    """
    if album_id:
        # Invalidate specific album
        cache_keys = [
            f"photos:album:detail:{album_id}",
            f"photos:album:photos:{album_id}",
            f"photos:album:count:{album_id}",
        ]
        for key in cache_keys:
            cache.delete(key)
        logger.info(f"Invalidated cache for album {album_id}")
    else:
        # Invalidate all album caches
        invalidate_cache_pattern("photos:album:")
        logger.info("Invalidated all album caches")
    
    # Always invalidate album list cache when any album changes
    cache.delete("photos:album:list")


def invalidate_photo_cache(photo_id: Optional[int] = None, album_id: Optional[int] = None):
    """
    Invalidate cache for photo(s).
    
    Args:
        photo_id: Specific photo ID to invalidate
        album_id: Album ID to invalidate photos for
    """
    if photo_id:
        cache_keys = [
            f"photos:photo:{photo_id}",
            f"photos:photo:thumb:{photo_id}",
        ]
        for key in cache_keys:
            cache.delete(key)
        logger.info(f"Invalidated cache for photo {photo_id}")
    
    if album_id:
        # Invalidate album's photo cache
        cache_keys = [
            f"photos:album:photos:{album_id}",
            f"photos:album:count:{album_id}",
        ]
        for key in cache_keys:
            cache.delete(key)
        logger.info(f"Invalidated photo cache for album {album_id}")


def conditional_cache_page(timeout: Optional[int] = None, key_prefix: str = ''):
    """
    Cache page conditionally based on user authentication.
    Only caches for anonymous users.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache key
    
    Returns:
        Decorated view function
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            # Only cache for anonymous users
            if request.user.is_authenticated:
                response = view_func(request, *args, **kwargs)
            else:
                # Use Django's cache_page for anonymous users
                cached_view = cache_page(timeout or CACHE_TTL, key_prefix=key_prefix)(view_func)
                response = cached_view(request, *args, **kwargs)
            
            # Add cache headers
            if not request.user.is_authenticated:
                patch_cache_control(response, public=True, max_age=timeout or CACHE_TTL)
            else:
                patch_cache_control(response, private=True, must_revalidate=True)
            
            return response
        
        return wrapper
    return decorator


def cache_album_photos(album_id: int, timeout: Optional[int] = None):
    """
    Cache photos for a specific album.
    
    Args:
        album_id: Album ID to cache photos for
        timeout: Cache timeout in seconds
    
    Returns:
        Cached photos queryset
    """
    cache_key = f"photos:album:photos:{album_id}"
    photos = cache.get(cache_key)
    
    if photos is None:
        from .models import Photo
        photos = list(Photo.objects.filter(
            album_id=album_id
        ).select_related('album').order_by('order', '-created_at'))
        
        cache.set(cache_key, photos, timeout or CACHE_TIMEOUTS['photo'])
        logger.debug(f"Cached {len(photos)} photos for album {album_id}")
    
    return photos


def cache_album_count(album_id: int, timeout: Optional[int] = None) -> int:
    """
    Cache photo count for an album.
    
    Args:
        album_id: Album ID to get count for
        timeout: Cache timeout in seconds
    
    Returns:
        Photo count for the album
    """
    cache_key = f"photos:album:count:{album_id}"
    count = cache.get(cache_key)
    
    if count is None:
        from .models import Photo
        count = Photo.objects.filter(album_id=album_id).count()
        cache.set(cache_key, count, timeout or CACHE_TIMEOUTS['photo_count'])
        logger.debug(f"Cached photo count ({count}) for album {album_id}")
    
    return count


def warm_album_cache(album_id: int):
    """
    Pre-warm cache for an album.
    
    Args:
        album_id: Album ID to warm cache for
    """
    from .models import Album
    
    try:
        album = Album.objects.prefetch_related('photos').get(pk=album_id)
        
        # Cache album details
        cache_key = f"photos:album:detail:{album_id}"
        cache.set(cache_key, album, CACHE_TIMEOUTS['album_detail'])
        
        # Cache photos
        cache_album_photos(album_id)
        
        # Cache photo count
        cache_album_count(album_id)
        
        logger.info(f"Warmed cache for album {album_id}")
        
    except Album.DoesNotExist:
        logger.warning(f"Album {album_id} not found for cache warming")


def get_cache_stats() -> dict:
    """
    Get cache statistics for monitoring.
    
    Returns:
        Dictionary with cache statistics
    """
    stats = {}
    
    for cache_name in caches:
        try:
            cache_backend = caches[cache_name]
            
            if hasattr(cache_backend, '_cache'):
                # Redis backend
                client = cache_backend._cache.get_client()
                info = client.info()
                stats[cache_name] = {
                    'type': 'redis',
                    'used_memory': info.get('used_memory_human', 'N/A'),
                    'connected_clients': info.get('connected_clients', 0),
                    'total_connections': info.get('total_connections_received', 0),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0),
                    'hit_rate': round(
                        info.get('keyspace_hits', 0) / 
                        max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1), 1) * 100, 
                        2
                    )
                }
            else:
                # Other backends
                stats[cache_name] = {
                    'type': type(cache_backend).__name__,
                    'available': True
                }
                
        except Exception as e:
            logger.error(f"Error getting cache stats for {cache_name}: {e}")
            stats[cache_name] = {'error': str(e)}
    
    return stats