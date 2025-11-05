"""
Massive.com (Polygon.io) Data Source Implementation.

Provides free financial market data:
- Rate Limit: ~100 requests/second (soft limit)
- Historical Data: 2 years at minute-level granularity
- Real-time Data: End-of-day only on free tier

API Documentation: https://polygon.io/docs
Client Library: https://github.com/massive-com/client-python
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List

from django.conf import settings
from polygon import RESTClient

from .base import DataNotFoundError, DataSourceError


class MassiveDataSource:
    name = "massive"
    display_name = "Massive.com"
    requires_api_key = True

    def __init__(self, api_key: str = None):
        if api_key is None:
            api_key = getattr(settings, "MASSIVE_API_KEY", None)

        if not api_key:
            raise DataSourceError("MASSIVE_API_KEY is required. Set in environment variables.")

        self.api_key = api_key
        self.client = RESTClient(api_key=api_key)

    def fetch_historical_prices(self, ticker: str, start_date: date, end_date: date) -> List[dict]:
        """
        Fetch historical price data from Massive.com (Polygon.io).

        Args:
            ticker: Stock ticker (e.g., AAPL, MSFT)
            start_date: Start date
            end_date: End date

        Returns:
            List of price dictionaries
        """
        try:
            aggs = self.client.get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="day",
                from_=start_date.strftime("%Y-%m-%d"),
                to=end_date.strftime("%Y-%m-%d"),
                adjusted=True,
                sort="asc",
                limit=50000,
            )

            results = []
            for agg in aggs:
                results.append(self._transform_result(ticker, agg))

            return results

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg:
                raise DataNotFoundError(f"Ticker '{ticker}' not found on Massive.com")
            raise DataSourceError(f"Failed to fetch data from Massive.com: {str(e)}")

    def _transform_result(self, ticker: str, agg) -> dict:
        """Transform Polygon.io Agg object to standard format."""
        if not hasattr(agg, "timestamp"):
            raise DataSourceError("Missing timestamp in response")

        timestamp = datetime.fromtimestamp(agg.timestamp / 1000)

        return {
            "ticker": ticker,
            "timestamp": timestamp,
            "open": Decimal(str(agg.open)),
            "high": Decimal(str(agg.high)),
            "low": Decimal(str(agg.low)),
            "close": Decimal(str(agg.close)),
            "volume": Decimal(str(agg.volume)) if agg.volume else None,
        }
