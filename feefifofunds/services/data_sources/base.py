"""
Base Data Source for fetching asset price data.
"""

import time
from abc import ABC, abstractmethod
from datetime import date
from typing import List

import requests


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
    Abstract base class for data sources.

    All data source implementations must inherit from this class.
    """

    name: str
    display_name: str
    base_url: str
    requires_api_key: bool = True

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    @abstractmethod
    def fetch_historical_prices(self, ticker: str, start_date: date, end_date: date) -> List[dict]:
        """
        Fetch historical OHLCV price data for an asset.

        Args:
            ticker: Asset ticker symbol
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            List of price dictionaries with keys: timestamp, open, high, low, close, volume

        Raises:
            DataSourceError: If data fetch fails
            RateLimitError: If rate limit is exceeded
            DataNotFoundError: If ticker not found
        """
        pass

    def _make_request(self, url: str, params: dict = None, max_retries: int = 3) -> dict:
        """
        Make HTTP request with retry logic.

        Args:
            url: Full URL to request
            params: Query parameters
            max_retries: Maximum number of retries

        Returns:
            JSON response as dictionary

        Raises:
            DataSourceError: If request fails after retries
            RateLimitError: If rate limit is hit
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)

                if response.status_code == 429:
                    raise RateLimitError(f"Rate limit exceeded for {self.name}")

                if response.status_code == 404:
                    raise DataNotFoundError(f"Data not found: {url}")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    raise DataSourceError(f"Request timeout after {max_retries} attempts")
                time.sleep(2**attempt)

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise DataSourceError(f"Request failed: {str(e)}")
                time.sleep(2**attempt)

        raise DataSourceError("Max retries exceeded")
