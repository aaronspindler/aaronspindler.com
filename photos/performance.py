"""
Performance monitoring and optimization utilities for the photos application.
"""
import time
import logging
import functools
from typing import Dict, Any, Callable, Optional
from django.db import connection, reset_queries
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Monitor and log performance metrics for the photos application.
    """
    
    def __init__(self):
        self.metrics = {
            'queries': [],
            'cache_hits': 0,
            'cache_misses': 0,
            'request_time': 0,
            'memory_usage': 0,
        }
    
    @contextmanager
    def monitor_queries(self, operation_name: str = "Unknown"):
        """
        Context manager to monitor database queries.
        
        Usage:
            with monitor.monitor_queries("fetch_albums"):
                albums = Album.objects.all()
        """
        initial_queries = len(connection.queries)
        start_time = time.time()
        
        try:
            yield
        finally:
            elapsed_time = time.time() - start_time
            query_count = len(connection.queries) - initial_queries
            
            if query_count > 0:
                queries = connection.queries[-query_count:]
                total_query_time = sum(float(q.get('time', 0)) for q in queries)
                
                logger.info(
                    f"[{operation_name}] {query_count} queries in {elapsed_time:.3f}s "
                    f"(DB: {total_query_time:.3f}s)"
                )
                
                # Log slow queries
                for query in queries:
                    query_time = float(query.get('time', 0))
                    if query_time > 0.1:  # Log queries slower than 100ms
                        logger.warning(
                            f"Slow query ({query_time:.3f}s): {query['sql'][:200]}..."
                        )
                
                # Store metrics
                self.metrics['queries'].append({
                    'operation': operation_name,
                    'count': query_count,
                    'total_time': total_query_time,
                    'elapsed_time': elapsed_time,
                })
    
    def log_cache_hit(self, key: str):
        """Log a cache hit."""
        self.metrics['cache_hits'] += 1
        logger.debug(f"Cache hit: {key}")
    
    def log_cache_miss(self, key: str):
        """Log a cache miss."""
        self.metrics['cache_misses'] += 1
        logger.debug(f"Cache miss: {key}")
    
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        if total == 0:
            return 0.0
        return (self.metrics['cache_hits'] / total) * 100
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics = {
            'queries': [],
            'cache_hits': 0,
            'cache_misses': 0,
            'request_time': 0,
            'memory_usage': 0,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of performance metrics."""
        return {
            'total_queries': sum(q['count'] for q in self.metrics['queries']),
            'total_query_time': sum(q['total_time'] for q in self.metrics['queries']),
            'cache_hit_rate': self.get_cache_hit_rate(),
            'cache_hits': self.metrics['cache_hits'],
            'cache_misses': self.metrics['cache_misses'],
            'operations': self.metrics['queries'],
        }


# Global monitor instance
monitor = PerformanceMonitor()


def profile_view(view_name: str):
    """
    Decorator to profile view performance.
    
    Usage:
        @profile_view("album_list")
        def album_list_view(request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            reset_queries()
            
            try:
                # Execute the view
                with monitor.monitor_queries(view_name):
                    response = func(*args, **kwargs)
                
                # Log performance metrics
                elapsed_time = time.time() - start_time
                query_count = len(connection.queries)
                
                logger.info(
                    f"View [{view_name}] completed in {elapsed_time:.3f}s "
                    f"with {query_count} queries"
                )
                
                # Store metrics for monitoring
                _store_performance_metrics(view_name, elapsed_time, query_count)
                
                return response
                
            except Exception as e:
                logger.error(f"Error in view [{view_name}]: {str(e)}", exc_info=True)
                raise
        
        return wrapper
    return decorator


def _store_performance_metrics(view_name: str, elapsed_time: float, query_count: int):
    """Store performance metrics in cache for monitoring."""
    metrics_key = f"performance:metrics:{view_name}"
    
    # Get existing metrics or create new
    metrics = cache.get(metrics_key, {
        'count': 0,
        'total_time': 0,
        'max_time': 0,
        'min_time': float('inf'),
        'total_queries': 0,
        'max_queries': 0,
    })
    
    # Update metrics
    metrics['count'] += 1
    metrics['total_time'] += elapsed_time
    metrics['max_time'] = max(metrics['max_time'], elapsed_time)
    metrics['min_time'] = min(metrics['min_time'], elapsed_time)
    metrics['total_queries'] += query_count
    metrics['max_queries'] = max(metrics['max_queries'], query_count)
    metrics['avg_time'] = metrics['total_time'] / metrics['count']
    metrics['avg_queries'] = metrics['total_queries'] / metrics['count']
    metrics['last_updated'] = timezone.now().isoformat()
    
    # Store for 1 hour
    cache.set(metrics_key, metrics, 3600)
    
    # Alert on slow performance
    if elapsed_time > 1.0:  # Alert if view takes more than 1 second
        logger.warning(
            f"Slow view detected: {view_name} took {elapsed_time:.3f}s "
            f"with {query_count} queries"
        )


def optimize_queryset(queryset):
    """
    Analyze and optimize a queryset.
    
    Returns the optimized queryset with suggestions logged.
    """
    model = queryset.model
    model_name = model.__name__
    
    # Check for common optimization opportunities
    suggestions = []
    
    # Check if select_related could be used
    for field in model._meta.fields:
        if field.many_to_one and field.related_model:
            if not queryset._prefetch_related_lookups:
                suggestions.append(
                    f"Consider using select_related('{field.name}') "
                    f"for {model_name}.{field.name}"
                )
    
    # Check if prefetch_related could be used
    for field in model._meta.get_fields():
        if field.one_to_many or field.many_to_many:
            if not queryset._prefetch_related_lookups:
                suggestions.append(
                    f"Consider using prefetch_related('{field.name}') "
                    f"for {model_name}.{field.name}"
                )
    
    # Log suggestions
    if suggestions:
        logger.info(f"Optimization suggestions for {model_name}:")
        for suggestion in suggestions:
            logger.info(f"  - {suggestion}")
    
    return queryset


class QueryCounter:
    """
    Context manager to count database queries.
    
    Usage:
        with QueryCounter() as counter:
            # Your code here
            pass
        print(f"Executed {counter.count} queries")
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.count = 0
        self.queries = []
    
    def __enter__(self):
        self.initial_queries = len(connection.queries)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.count = len(connection.queries) - self.initial_queries
        
        if self.count > 0:
            self.queries = connection.queries[-self.count:]
            
            if self.verbose:
                for i, query in enumerate(self.queries, 1):
                    print(f"Query {i} ({query.get('time', 'N/A')}s):")
                    print(f"  {query['sql'][:200]}...")
                print(f"Total: {self.count} queries")


def log_slow_queries(threshold: float = 0.1):
    """
    Decorator to log slow database queries.
    
    Args:
        threshold: Query time threshold in seconds
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            reset_queries()
            
            result = func(*args, **kwargs)
            
            # Check for slow queries
            for query in connection.queries:
                query_time = float(query.get('time', 0))
                if query_time > threshold:
                    logger.warning(
                        f"Slow query in {func.__name__} ({query_time:.3f}s): "
                        f"{query['sql'][:200]}..."
                    )
            
            return result
        
        return wrapper
    return decorator


def get_performance_report() -> Dict[str, Any]:
    """
    Generate a comprehensive performance report.
    """
    from django.core.cache import caches
    from photos.cache import get_cache_stats
    
    report = {
        'timestamp': timezone.now().isoformat(),
        'database': {
            'query_count': len(connection.queries),
            'slow_queries': [],
        },
        'cache': get_cache_stats(),
        'views': {},
        'summary': monitor.get_summary(),
    }
    
    # Analyze recent queries
    for query in connection.queries[-100:]:  # Last 100 queries
        query_time = float(query.get('time', 0))
        if query_time > 0.1:  # Queries slower than 100ms
            report['database']['slow_queries'].append({
                'time': query_time,
                'sql': query['sql'][:200],
            })
    
    # Get view metrics from cache
    view_names = ['album_list', 'album_detail', 'photo_view']
    for view_name in view_names:
        metrics_key = f"performance:metrics:{view_name}"
        metrics = cache.get(metrics_key)
        if metrics:
            report['views'][view_name] = metrics
    
    return report


# Middleware for request performance tracking
class PerformanceMiddleware:
    """
    Middleware to track request performance.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Start timing
        start_time = time.time()
        reset_queries()
        
        # Process request
        response = self.get_response(request)
        
        # Calculate metrics
        elapsed_time = time.time() - start_time
        query_count = len(connection.queries)
        
        # Log performance
        if elapsed_time > 1.0:  # Log slow requests
            logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"took {elapsed_time:.3f}s with {query_count} queries"
            )
        
        # Add performance headers (in development only)
        if settings.DEBUG:
            response['X-DB-Query-Count'] = str(query_count)
            response['X-Response-Time'] = f"{elapsed_time:.3f}"
        
        return response