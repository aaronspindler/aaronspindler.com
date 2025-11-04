"""
Finnhub Data Source Implementation.

Finnhub.io provides free financial market data with generous rate limits:
- Rate Limit: 60 API calls per minute
- Historical Data: 1 year per request
- Real-time Data: Yes (within rate limits)
- Free Tier: Best for real-time data and reasonable historical coverage

API Documentation: https://finnhub.io/docs/api
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from django.conf import settings

from .base import BaseDataSource, DataNotFoundError, DataSourceError
from .dto import FundDataDTO, HoldingDataDTO, PerformanceDataDTO


class FinnhubDataSource(BaseDataSource):
    """
    Finnhub.io data source implementation.

    Provides access to stock/ETF data including:
    - Company profile (basic fund info)
    - Historical candles (OHLCV data)
    - Quote data (current prices)

    Free tier limitations:
    - 60 API calls per minute
    - 1 year of historical data per request
    - Real-time data included
    """

    name = "finnhub"
    display_name = "Finnhub"
    base_url = "https://finnhub.io/api/v1"
    requires_api_key = True
    rate_limit_requests = 60
    rate_limit_period = 60

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Finnhub data source.

        Args:
            api_key: Finnhub API key (required)
        """
        if api_key is None:
            api_key = getattr(settings, "FINNHUB_API_KEY", None)

        if not api_key:
            raise DataSourceError("Finnhub API key is required. Set FINNHUB_API_KEY in settings.")

        super().__init__(api_key=api_key)

    def _make_finnhub_request(self, endpoint: str, params: dict = None) -> dict:
        """
        Make a request to Finnhub API.

        Args:
            endpoint: API endpoint (e.g., '/stock/profile2')
            params: Query parameters

        Returns:
            Response JSON as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params["token"] = self.api_key

        return self._make_request(url, params=params)

    def fetch_fund_info(self, ticker: str) -> FundDataDTO:
        """
        Fetch basic fund/stock information from Finnhub.

        Uses the company profile endpoint to get basic info.

        Args:
            ticker: Stock/ETF ticker symbol

        Returns:
            FundDataDTO with fund information
        """
        try:
            profile_data = self._make_finnhub_request("/stock/profile2", params={"symbol": ticker})

            if not profile_data or not profile_data.get("name"):
                raise DataNotFoundError(f"No data found for ticker {ticker}")

            quote_data = self._make_finnhub_request("/quote", params={"symbol": ticker})

            return FundDataDTO(
                ticker=ticker,
                name=profile_data.get("name", ticker),
                description=profile_data.get("description"),
                exchange=profile_data.get("exchange"),
                currency=profile_data.get("currency", "USD"),
                current_price=Decimal(str(quote_data.get("c", 0))) if quote_data.get("c") else None,
                previous_close=Decimal(str(quote_data.get("pc", 0))) if quote_data.get("pc") else None,
                isin=profile_data.get("isin"),
                website=profile_data.get("weburl"),
                aum=Decimal(str(profile_data.get("marketCapitalization", 0)))
                if profile_data.get("marketCapitalization")
                else None,
                source=self.name,
            )

        except DataNotFoundError:
            raise
        except Exception as e:
            raise DataSourceError(f"Failed to fetch fund info for {ticker}: {str(e)}")

    def fetch_historical_prices(
        self, ticker: str, start_date: date, end_date: date, interval: str = "D"
    ) -> List[PerformanceDataDTO]:
        """
        Fetch historical price data from Finnhub.

        Uses the stock candles endpoint to get OHLCV data.

        Args:
            ticker: Stock/ETF ticker symbol
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval (D=daily, W=weekly, M=monthly)

        Returns:
            List of PerformanceDataDTO objects
        """
        try:
            resolution_map = {"D": "D", "1D": "D", "W": "W", "1W": "W", "M": "M", "1M": "M"}

            resolution = resolution_map.get(interval, "D")

            start_timestamp = int(start_date.strftime("%s"))
            end_timestamp = int(end_date.strftime("%s"))

            candles_data = self._make_finnhub_request(
                "/stock/candle",
                params={"symbol": ticker, "resolution": resolution, "from": start_timestamp, "to": end_timestamp},
            )

            if candles_data.get("s") != "ok":
                raise DataNotFoundError(f"No historical data found for ticker {ticker}")

            timestamps = candles_data.get("t", [])
            opens = candles_data.get("o", [])
            highs = candles_data.get("h", [])
            lows = candles_data.get("l", [])
            closes = candles_data.get("c", [])
            volumes = candles_data.get("v", [])

            performance_data = []
            for i in range(len(timestamps)):
                perf_date = date.fromtimestamp(timestamps[i])

                performance_data.append(
                    PerformanceDataDTO(
                        ticker=ticker,
                        date=perf_date,
                        open_price=Decimal(str(opens[i])),
                        high_price=Decimal(str(highs[i])),
                        low_price=Decimal(str(lows[i])),
                        close_price=Decimal(str(closes[i])),
                        volume=int(volumes[i]),
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

        Note: Finnhub free tier does not provide holdings data for ETFs/funds.
        This is a placeholder that raises DataNotFoundError.

        Args:
            ticker: Fund ticker symbol

        Returns:
            List of HoldingDataDTO objects

        Raises:
            DataNotFoundError: Holdings not available on free tier
        """
        raise DataNotFoundError(f"Holdings data not available for {ticker} on Finnhub free tier")

    def fetch_quote(self, ticker: str) -> dict:
        """
        Fetch current quote data for a ticker.

        Returns real-time quote with current price, previous close, and other metrics.

        Args:
            ticker: Stock/ETF ticker symbol

        Returns:
            Dictionary with quote data
        """
        try:
            return self._make_finnhub_request("/quote", params={"symbol": ticker})
        except Exception as e:
            raise DataSourceError(f"Failed to fetch quote for {ticker}: {str(e)}")

    def fetch_recent_days(self, ticker: str, days: int = 365) -> List[PerformanceDataDTO]:
        """
        Convenience method to fetch recent historical data.

        Args:
            ticker: Stock/ETF ticker symbol
            days: Number of days to fetch (default: 365)

        Returns:
            List of PerformanceDataDTO objects
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        return self.fetch_historical_prices(ticker, start_date, end_date)
