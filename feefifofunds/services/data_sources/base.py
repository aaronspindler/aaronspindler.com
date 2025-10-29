"""
Base Data Source Abstract Class.

Provides the foundation for all external data source integrations.
"""

import time
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

import requests
from django.core.cache import cache

from feefifofunds.models import DataSource, DataSync

from .dto import FundDataDTO, HoldingDataDTO, PerformanceDataDTO


class DataSourceError(Exception):
    """Base exception for data source errors."""

    pass


class RateLimitError(DataSourceError):
    """Raised when rate limit is exceeded."""

    pass


class DataNotFoundError(DataSourceError):
    """Raised when requested data is not found."""

    pass


class BaseDataSource(ABC):
    """
    Abstract base class for all data sources.

    All data source implementations (Yahoo Finance, Alpha Vantage, etc.)
    must inherit from this class and implement the abstract methods.

    Attributes:
        name: Unique identifier for this data source
        display_name: Human-readable name
        base_url: Base URL for API requests
        requires_api_key: Whether an API key is required
        rate_limit_requests: Maximum requests allowed
        rate_limit_period: Time period for rate limit (seconds)
    """

    # Subclasses must define these
    name: str = NotImplemented
    display_name: str = NotImplemented
    base_url: str = NotImplemented
    requires_api_key: bool = False
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    request_timeout: int = 30  # default timeout in seconds

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the data source.

        Args:
            api_key: Optional API key for authenticated requests
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "FeeFiFoFunds/1.0"})

        # Get or create DataSource model instance
        self.data_source_model, created = DataSource.objects.get_or_create(
            name=self.name,
            defaults={
                "display_name": self.display_name,
                "source_type": DataSource.SourceType.API,
                "base_url": self.base_url,
                "api_key_required": self.requires_api_key,
                "rate_limit_requests": self.rate_limit_requests,
                "rate_limit_period_seconds": self.rate_limit_period,
            },
        )

    def can_make_request(self) -> bool:
        """
        Check if we can make a request without exceeding rate limits.

        Uses simple Redis-backed rate limiting. For production with multiple workers,
        consider using django-ratelimit for atomic operations.

        Returns:
            True if request can be made, False otherwise
        """
        # Use Redis cache for rate limiting
        key = f"datasource_ratelimit:{self.name}"

        # Get current count
        current_count = cache.get(key, 0)

        # Check if we're under the limit
        if current_count < self.rate_limit_requests:
            # Increment counter
            cache.set(key, current_count + 1, self.rate_limit_period)
            return True

        return False

    def record_request(self, success: bool = True, error_message: str = ""):
        """
        Record a request to this data source for rate limiting and monitoring.

        Args:
            success: Whether the request was successful
            error_message: Error message if request failed
        """
        self.data_source_model.record_request(success=success, error_message=error_message)

    def wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits."""
        if not self.can_make_request():
            wait_time = self.rate_limit_period
            print(f"Rate limit reached for {self.name}, waiting {wait_time} seconds...")
            time.sleep(wait_time)

    def _make_request(self, url: str, params: dict = None, timeout: int = None) -> dict:
        """
        Make an HTTP GET request with error handling and rate limiting.

        Args:
            url: URL to request
            params: Query parameters
            timeout: Request timeout in seconds (uses class default if not specified)

        Returns:
            Response JSON as dictionary

        Raises:
            RateLimitError: If rate limit is exceeded
            DataSourceError: If request fails
        """
        if timeout is None:
            timeout = self.request_timeout

        self.wait_for_rate_limit()

        try:
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            self.record_request(success=True)
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Enhanced error message with context
            error_context = f"HTTP {e.response.status_code} error for {url}"
            if params:
                error_context += f" with params={params}"

            # Include response body (truncated)
            if e.response.text:
                error_context += f": {e.response.text[:200]}"

            if e.response.status_code == 429:
                self.record_request(success=False, error_message=error_context)
                raise RateLimitError(f"Rate limit exceeded for {self.name}: {error_context}")

            self.record_request(success=False, error_message=error_context)
            raise DataSourceError(error_context)
        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {timeout}s for {url}"
            if params:
                error_msg += f" with params={params}"
            self.record_request(success=False, error_message=error_msg)
            raise DataSourceError(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed for {url}: {str(e)}"
            if params:
                error_msg += f" with params={params}"
            self.record_request(success=False, error_message=error_msg)
            raise DataSourceError(error_msg)
        except ValueError as e:
            error_msg = f"Invalid JSON response from {url}: {str(e)}"
            self.record_request(success=False, error_message=error_msg)
            raise DataSourceError(error_msg)

    def _get_cached_or_fetch(self, cache_key: str, fetch_func, cache_timeout: int = 3600):
        """
        Get data from cache or fetch and cache it.

        Args:
            cache_key: Cache key
            fetch_func: Function to call if cache miss
            cache_timeout: Cache timeout in seconds

        Returns:
            Cached or fetched data
        """
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        data = fetch_func()
        cache.set(cache_key, data, cache_timeout)
        return data

    # Abstract methods that subclasses must implement

    @abstractmethod
    def fetch_fund_info(self, ticker: str) -> FundDataDTO:
        """
        Fetch basic fund information.

        Args:
            ticker: Fund ticker symbol

        Returns:
            FundDataDTO with fund information

        Raises:
            DataNotFoundError: If fund not found
            DataSourceError: If fetch fails
        """
        pass

    @abstractmethod
    def fetch_historical_prices(
        self, ticker: str, start_date: date, end_date: date, interval: str = "1D"
    ) -> List[PerformanceDataDTO]:
        """
        Fetch historical price data.

        Args:
            ticker: Fund ticker symbol
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval (1D, 1W, 1M, etc.)

        Returns:
            List of PerformanceDataDTO objects

        Raises:
            DataNotFoundError: If data not found
            DataSourceError: If fetch fails
        """
        pass

    @abstractmethod
    def fetch_holdings(self, ticker: str) -> List[HoldingDataDTO]:
        """
        Fetch fund holdings data.

        Args:
            ticker: Fund ticker symbol

        Returns:
            List of HoldingDataDTO objects

        Raises:
            DataNotFoundError: If holdings not available
            DataSourceError: If fetch fails
        """
        pass

    # Optional methods with default implementations

    def validate_data(self, data: any) -> bool:
        """
        Validate fetched data.

        Args:
            data: Data to validate

        Returns:
            True if valid, False otherwise
        """
        # Basic validation - subclasses can override
        if data is None:
            return False
        if isinstance(data, (list, tuple)) and len(data) == 0:
            return False
        return True

    def supports_feature(self, feature: str) -> bool:
        """
        Check if this data source supports a specific feature.

        Args:
            feature: Feature name (e.g., 'historical', 'realtime', 'holdings')

        Returns:
            True if feature is supported
        """
        feature_map = {
            "historical": self.data_source_model.supports_historical_data,
            "realtime": self.data_source_model.supports_realtime_data,
            "holdings": self.data_source_model.supports_holdings,
            "fundamentals": self.data_source_model.supports_fundamentals,
        }
        return feature_map.get(feature, False)

    def create_sync_record(self, sync_type: str, fund=None, request_params: dict = None) -> DataSync:
        """
        Create a DataSync record to track this synchronization.

        Args:
            sync_type: Type of sync (FUND_INFO, PRICES, HOLDINGS, etc.)
            fund: Optional Fund instance
            request_params: Optional request parameters

        Returns:
            DataSync instance
        """
        return DataSync.objects.create(
            data_source=self.data_source_model,
            fund=fund,
            sync_type=sync_type,
            status=DataSync.Status.IN_PROGRESS,
            request_params=request_params or {},
        )

    def __str__(self) -> str:
        """String representation."""
        return f"{self.display_name} ({self.name})"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"<{self.__class__.__name__}: {self.name}>"
