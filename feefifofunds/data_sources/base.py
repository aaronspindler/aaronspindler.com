"""
Abstract base class for fund data sources.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from django.core.cache import cache

from .dto import FundDataDTO

logger = logging.getLogger(__name__)


class BaseDataSource(ABC):
    """
    Abstract base class for all fund data sources.

    Subclasses must implement:
    - fetch_fund(ticker)
    - supports_fund_type(fund_type)
    """

    def __init__(self, cache_timeout: int = 86400, enable_cache: bool = True):
        """
        Initialize the data source.

        Args:
            cache_timeout: Cache timeout in seconds (default: 24 hours)
            enable_cache: Whether to use caching (default: True)
        """
        self.cache_timeout = cache_timeout
        self.enable_cache = enable_cache
        self.source_name = self.__class__.__name__
        self._rate_limit_delay = 0.0  # Delay between requests in seconds

    @abstractmethod
    def fetch_fund(self, ticker: str) -> Optional[FundDataDTO]:
        """
        Fetch fund data for a single ticker.

        Args:
            ticker: Fund ticker symbol

        Returns:
            FundDataDTO if found, None otherwise

        Raises:
            Exception: If the fetch fails for any reason
        """
        pass

    @abstractmethod
    def supports_fund_type(self, fund_type: str) -> bool:
        """
        Check if this data source supports a specific fund type.

        Args:
            fund_type: "ETF" or "MUTUAL_FUND"

        Returns:
            True if supported, False otherwise
        """
        pass

    def fetch_multiple(self, tickers: List[str]) -> List[FundDataDTO]:
        """
        Fetch multiple funds. Default implementation calls fetch_fund repeatedly.

        Args:
            tickers: List of ticker symbols

        Returns:
            List of FundDataDTO objects (skips failed fetches)
        """
        results = []
        for i, ticker in enumerate(tickers):
            try:
                logger.info(f"[{self.source_name}] Fetching {ticker} ({i+1}/{len(tickers)})")
                fund_data = self.fetch_fund(ticker)
                if fund_data:
                    results.append(fund_data)
                else:
                    logger.warning(f"[{self.source_name}] No data found for {ticker}")

                # Rate limiting delay
                if self._rate_limit_delay > 0 and i < len(tickers) - 1:
                    time.sleep(self._rate_limit_delay)

            except Exception as e:
                logger.error(f"[{self.source_name}] Error fetching {ticker}: {e}")
                continue

        return results

    def search_funds(self, query: str) -> List[FundDataDTO]:
        """
        Search for funds by name or ticker.

        Default implementation returns empty list (not supported).
        Override in subclasses that support search.

        Args:
            query: Search query string

        Returns:
            List of matching FundDataDTO objects
        """
        logger.warning(f"[{self.source_name}] Search not implemented")
        return []

    def _get_cache_key(self, ticker: str) -> str:
        """Generate a cache key for a ticker."""
        return f"fund_data:{self.source_name}:{ticker}"

    def _get_from_cache(self, ticker: str) -> Optional[FundDataDTO]:
        """Get fund data from cache if available."""
        if not self.enable_cache:
            return None

        cache_key = self._get_cache_key(ticker)
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(f"[{self.source_name}] Cache hit for {ticker}")
            return cached_data

        return None

    def _save_to_cache(self, ticker: str, fund_data: FundDataDTO):
        """Save fund data to cache."""
        if not self.enable_cache or not fund_data:
            return

        cache_key = self._get_cache_key(ticker)
        cache.set(cache_key, fund_data, self.cache_timeout)
        logger.debug(f"[{self.source_name}] Cached data for {ticker}")

    def _apply_rate_limit(self):
        """Apply rate limiting delay if configured."""
        if self._rate_limit_delay > 0:
            time.sleep(self._rate_limit_delay)

    def get_source_info(self) -> dict:
        """
        Get information about this data source.

        Returns:
            Dict with source metadata
        """
        return {
            "name": self.source_name,
            "cache_enabled": self.enable_cache,
            "cache_timeout": self.cache_timeout,
            "rate_limit_delay": self._rate_limit_delay,
            "supports_etf": self.supports_fund_type("ETF"),
            "supports_mutual_fund": self.supports_fund_type("MUTUAL_FUND"),
        }

    def __repr__(self):
        return f"{self.source_name}(cache={self.enable_cache})"
