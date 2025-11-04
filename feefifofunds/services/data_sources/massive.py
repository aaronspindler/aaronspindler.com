"""
Massive.com (formerly Polygon.io) Data Source Implementation.

Massive.com provides free financial market data with generous limits:
- Rate Limit: ~100 requests/second (soft limit, no hard cap)
- Historical Data: 2 years at minute-level granularity
- Real-time Data: No (end-of-day only on free tier)
- Free Tier: Best for historical data and batch processing

API Documentation: https://massive.com/docs/
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from django.conf import settings

from .base import BaseDataSource, DataNotFoundError, DataSourceError
from .dto import FundDataDTO, HoldingDataDTO, PerformanceDataDTO


class MassiveDataSource(BaseDataSource):
    """
    Massive.com (formerly Polygon.io) data source implementation.

    Provides access to historical stock/ETF data including:
    - Ticker details (basic fund info)
    - Aggregate bars (OHLCV data)
    - Previous close data

    Free tier features:
    - Unlimited requests (~100/sec soft limit)
    - 2 years of historical data
    - End-of-day data only (no real-time on free tier)
    """

    name = "massive"
    display_name = "Massive.com"
    base_url = "https://api.polygon.io"
    requires_api_key = True
    rate_limit_requests = 100
    rate_limit_period = 1

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Massive data source.

        Args:
            api_key: Massive.com API key (required)
        """
        if api_key is None:
            api_key = getattr(settings, "MASSIVE_API_KEY", None)

        if not api_key:
            raise DataSourceError("Massive.com API key is required. Set MASSIVE_API_KEY in settings.")

        super().__init__(api_key=api_key)

    def _make_massive_request(self, endpoint: str, params: dict = None) -> dict:
        """
        Make a request to Massive.com API.

        Args:
            endpoint: API endpoint (e.g., '/v3/reference/tickers/AAPL')
            params: Query parameters

        Returns:
            Response JSON as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params["apiKey"] = self.api_key

        return self._make_request(url, params=params)

    def fetch_fund_info(self, ticker: str) -> FundDataDTO:
        """
        Fetch basic fund/stock information from Massive.com.

        Uses the ticker details endpoint to get basic info.

        Args:
            ticker: Stock/ETF ticker symbol

        Returns:
            FundDataDTO with fund information
        """
        try:
            ticker_data = self._make_massive_request(f"/v3/reference/tickers/{ticker}")

            if not ticker_data or ticker_data.get("status") != "OK":
                raise DataNotFoundError(f"No data found for ticker {ticker}")

            results = ticker_data.get("results", {})

            prev_close_data = self._make_massive_request(f"/v2/aggs/ticker/{ticker}/prev")

            prev_close = None
            if prev_close_data.get("status") == "OK" and prev_close_data.get("results"):
                prev_close = Decimal(str(prev_close_data["results"][0].get("c", 0)))

            return FundDataDTO(
                ticker=ticker,
                name=results.get("name", ticker),
                description=results.get("description"),
                exchange=results.get("primary_exchange"),
                currency=results.get("currency_name", "USD"),
                current_price=prev_close,
                previous_close=prev_close,
                website=results.get("homepage_url"),
                aum=Decimal(str(results.get("market_cap", 0))) / 1_000_000 if results.get("market_cap") else None,
                source=self.name,
            )

        except DataNotFoundError:
            raise
        except Exception as e:
            raise DataSourceError(f"Failed to fetch fund info for {ticker}: {str(e)}")

    def fetch_historical_prices(
        self, ticker: str, start_date: date, end_date: date, interval: str = "1D"
    ) -> List[PerformanceDataDTO]:
        """
        Fetch historical price data from Massive.com.

        Uses the aggregate bars endpoint to get OHLCV data.
        Free tier provides 2 years of historical data.

        Args:
            ticker: Stock/ETF ticker symbol
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval (1D=daily, 1W=weekly, 1M=monthly)

        Returns:
            List of PerformanceDataDTO objects
        """
        try:
            timespan_map = {
                "D": "day",
                "1D": "day",
                "W": "week",
                "1W": "week",
                "M": "month",
                "1M": "month",
            }

            timespan = timespan_map.get(interval, "day")
            multiplier = 1

            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            aggs_data = self._make_massive_request(
                f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{start_str}/{end_str}",
                params={"adjusted": "true", "sort": "asc", "limit": 50000},
            )

            if aggs_data.get("status") != "OK" or not aggs_data.get("results"):
                raise DataNotFoundError(f"No historical data found for ticker {ticker}")

            performance_data = []
            for bar in aggs_data.get("results", []):
                timestamp = bar.get("t") / 1000
                perf_date = datetime.fromtimestamp(timestamp).date()

                performance_data.append(
                    PerformanceDataDTO(
                        ticker=ticker,
                        date=perf_date,
                        open_price=Decimal(str(bar.get("o"))),
                        high_price=Decimal(str(bar.get("h"))),
                        low_price=Decimal(str(bar.get("l"))),
                        close_price=Decimal(str(bar.get("c"))),
                        volume=int(bar.get("v", 0)),
                        interval=interval,
                        source=self.name,
                    )
                )

            return performance_data

        except DataNotFoundError:
            raise
        except Exception as e:
            raise DataSourceError(f"Failed to fetch historical prices for {ticker}: {str(e)}")

    def fetch_holdings(self, ticker: str) -> List[HoldingDataDTO]:
        """
        Fetch fund holdings data.

        Note: Massive.com free tier does not provide holdings data for ETFs/funds.
        This is a placeholder that raises DataNotFoundError.

        Args:
            ticker: Fund ticker symbol

        Returns:
            List of HoldingDataDTO objects

        Raises:
            DataNotFoundError: Holdings not available on free tier
        """
        raise DataNotFoundError(f"Holdings data not available for {ticker} on Massive.com free tier")

    def fetch_previous_close(self, ticker: str) -> dict:
        """
        Fetch previous close data for a ticker.

        Returns the previous trading day's OHLCV data.

        Args:
            ticker: Stock/ETF ticker symbol

        Returns:
            Dictionary with previous close data
        """
        try:
            return self._make_massive_request(f"/v2/aggs/ticker/{ticker}/prev")
        except Exception as e:
            raise DataSourceError(f"Failed to fetch previous close for {ticker}: {str(e)}")

    def fetch_recent_days(self, ticker: str, days: int = 730) -> List[PerformanceDataDTO]:
        """
        Convenience method to fetch recent historical data.

        Free tier supports up to 2 years (730 days) of data.

        Args:
            ticker: Stock/ETF ticker symbol
            days: Number of days to fetch (default: 730, max: 730 for free tier)

        Returns:
            List of PerformanceDataDTO objects
        """
        days = min(days, 730)
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        return self.fetch_historical_prices(ticker, start_date, end_date)

    def fetch_daily_open_close(self, ticker: str, target_date: date) -> dict:
        """
        Fetch open/close data for a specific date.

        Args:
            ticker: Stock/ETF ticker symbol
            target_date: Date to fetch data for

        Returns:
            Dictionary with open/close data
        """
        try:
            date_str = target_date.strftime("%Y-%m-%d")
            return self._make_massive_request(f"/v1/open-close/{ticker}/{date_str}")
        except Exception as e:
            raise DataSourceError(f"Failed to fetch open/close for {ticker} on {target_date}: {str(e)}")
