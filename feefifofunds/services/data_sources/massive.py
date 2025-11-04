"""
Massive.com (formerly Polygon.io) Data Source Implementation.

Massive.com provides free financial market data with generous limits:
- Rate Limit: ~100 requests/second (soft limit, no hard cap)
- Historical Data: 2 years at minute-level granularity
- Real-time Data: No (end-of-day only on free tier)
- Free Tier: Best for historical data and batch processing

API Documentation: https://massive.com/docs/
"""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from django.conf import settings

from .base import BaseDataSource, DataNotFoundError, DataSourceError
from .dto import FundDataDTO, HoldingDataDTO, PerformanceDataDTO

MAX_FREE_TIER_DAYS = 730


class MassiveDataSource(BaseDataSource):
    name = "massive"
    display_name = "Massive.com"
    base_url = "https://api.polygon.io"
    requires_api_key = True
    rate_limit_requests = 100
    rate_limit_period = 1

    def __init__(self, api_key: Optional[str] = None):
        if api_key is None:
            api_key = getattr(settings, "MASSIVE_API_KEY", None)

        if not api_key:
            raise DataSourceError("MASSIVE_API_KEY is required. Set in environment variables or settings.")

        super().__init__(api_key=api_key)

    @staticmethod
    def _validate_ticker(ticker: str) -> None:
        if not ticker or not isinstance(ticker, str):
            raise DataSourceError("Ticker must be a non-empty string")
        if not re.match(r"^[A-Z0-9.^-]+$", ticker.upper()):
            raise DataSourceError(f"Invalid ticker format: {ticker}")

    @staticmethod
    def _validate_date_range(start_date: date, end_date: date) -> None:
        if start_date > end_date:
            raise DataSourceError(f"Start date ({start_date}) must be before end date ({end_date})")
        if (end_date - start_date).days > MAX_FREE_TIER_DAYS:
            raise DataSourceError(f"Date range exceeds free tier limit of {MAX_FREE_TIER_DAYS} days")

    def _make_massive_request(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params["apiKey"] = self.api_key

        return self._make_request(url, params=params)

    def fetch_fund_info(self, ticker: str) -> FundDataDTO:
        self._validate_ticker(ticker)

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
        self._validate_ticker(ticker)
        self._validate_date_range(start_date, end_date)

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
        raise DataNotFoundError(f"Holdings data not available for {ticker} on Massive.com free tier")

    def fetch_previous_close(self, ticker: str) -> dict:
        self._validate_ticker(ticker)
        try:
            return self._make_massive_request(f"/v2/aggs/ticker/{ticker}/prev")
        except Exception as e:
            raise DataSourceError(f"Failed to fetch previous close for {ticker}: {str(e)}")

    def fetch_recent_days(self, ticker: str, days: int = MAX_FREE_TIER_DAYS) -> List[PerformanceDataDTO]:
        days = min(days, MAX_FREE_TIER_DAYS)
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        return self.fetch_historical_prices(ticker, start_date, end_date)

    def fetch_daily_open_close(self, ticker: str, target_date: date) -> dict:
        self._validate_ticker(ticker)
        try:
            date_str = target_date.strftime("%Y-%m-%d")
            return self._make_massive_request(f"/v1/open-close/{ticker}/{date_str}")
        except Exception as e:
            raise DataSourceError(f"Failed to fetch open/close for {ticker} on {target_date}: {str(e)}")
