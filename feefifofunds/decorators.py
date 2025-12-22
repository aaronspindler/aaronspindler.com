import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar

from django.core.cache import cache
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def rate_limit(calls_per_second: float = 1.0) -> Callable[[F], F]:
    min_interval = 1.0 / calls_per_second
    last_called = {}  # Track last call time per function

    def decorator(func: F) -> F:
        func_key = f"{func.__module__}.{func.__name__}"
        last_called[func_key] = 0.0

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Calculate time to wait
            elapsed = time.time() - last_called[func_key]
            left_to_wait = min_interval - elapsed

            if left_to_wait > 0:
                logger.debug(f"Rate limiting {func_key}: waiting {left_to_wait:.2f}s")
                time.sleep(left_to_wait)

            result = func(*args, **kwargs)
            last_called[func_key] = time.time()

            return result

        return wrapper

    return decorator


def retry_with_backoff(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 60,
    exception_types: tuple | None = None,
) -> Callable[[F], F]:
    if exception_types is None:
        exception_types = (Exception,)

    def decorator(func: F) -> F:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exception_types),
            reraise=True,
        )
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                logger.warning(f"Retry attempt for {func.__name__}: {e}")
                raise

        return wrapper

    return decorator


def cached_result(timeout: int = 300, key_prefix: str = None) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            prefix = key_prefix or f"{func.__module__}.{func.__name__}"
            cache_key = f"{prefix}:{args}:{kwargs}"

            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return result

            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            logger.debug(f"Cached result for {cache_key}")

            return result

        def clear_cache(*args, **kwargs):
            prefix = key_prefix or f"{func.__module__}.{func.__name__}"
            cache_key = f"{prefix}:{args}:{kwargs}"
            cache.delete(cache_key)
            logger.debug(f"Cleared cache for {cache_key}")

        wrapper.clear_cache = clear_cache
        return wrapper

    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type[Exception] = Exception,
) -> Callable[[F], F]:
    from pybreaker import CircuitBreaker as PyBreaker

    def decorator(func: F) -> F:
        breaker = PyBreaker(
            fail_max=failure_threshold,
            reset_timeout=recovery_timeout,
            exclude=[expected_exception],
            name=f"{func.__module__}.{func.__name__}",
        )

        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker(func)(*args, **kwargs)

        wrapper.breaker = breaker
        wrapper.is_open = lambda: breaker.state == "open"
        wrapper.is_closed = lambda: breaker.state == "closed"
        wrapper.failure_count = lambda: breaker.fail_counter

        return wrapper

    return decorator


def timed_execution(log_slow_threshold: float = 1.0) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time

                if elapsed > log_slow_threshold:
                    logger.warning(f"{func.__name__} took {elapsed:.2f}s (threshold: {log_slow_threshold}s)")
                else:
                    logger.debug(f"{func.__name__} completed in {elapsed:.2f}s")

                return result

            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"{func.__name__} failed after {elapsed:.2f}s: {e}")
                raise

        return wrapper

    return decorator


def validate_inputs(validator_class: type) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                validated = validator_class(**kwargs)
                kwargs = validated.model_dump()
            except Exception as e:
                logger.error(f"Input validation failed for {func.__name__}: {e}")
                raise ValueError(f"Invalid input: {e}") from e

            return func(*args, **kwargs)

        return wrapper

    return decorator


def batch_process(batch_size: int = 1000) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(items, *args, **kwargs):
            total_items = len(items)
            processed = 0

            for i in range(0, total_items, batch_size):
                batch = items[i : i + batch_size]
                result = func(batch, *args, **kwargs)

                processed += len(batch)
                logger.debug(f"Processed batch: {processed}/{total_items} items")

                yield result

        return wrapper

    return decorator


def async_task(queue_name: str = "default") -> Callable[[F], F]:
    from celery import shared_task

    def decorator(func: F) -> F:
        return shared_task(
            bind=True,
            name=f"feefifofunds.{func.__name__}",
            queue=queue_name,
            max_retries=3,
            default_retry_delay=60,
        )(func)

    return decorator


def api_call(
    rate_limit_per_second: float = 1.0,
    max_retries: int = 3,
    cache_timeout: int = 0,
) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        decorated = func

        if cache_timeout > 0:
            decorated = cached_result(timeout=cache_timeout)(decorated)

        # Add retry logic
        decorated = retry_with_backoff(max_attempts=max_retries)(decorated)

        decorated = rate_limit(calls_per_second=rate_limit_per_second)(decorated)

        decorated = timed_execution()(decorated)

        return decorated

    return decorator


def database_operation(use_transaction: bool = True) -> Callable[[F], F]:
    from django.db import transaction

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if use_transaction:
                with transaction.atomic():
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator
