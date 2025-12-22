import time
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List

from django.conf import settings
from polygon import RESTClient

from .base import DataNotFoundError, DataSourceError

MAX_FREE_TIER_DAYS = 730
RATE_LIMIT_DELAY_SECONDS = 12


class MassiveDataSource:
    name = "massive"
    display_name = "Massive.com"
    requires_api_key = True
    max_free_tier_days = MAX_FREE_TIER_DAYS
    rate_limit_delay = RATE_LIMIT_DELAY_SECONDS

    def __init__(self, api_key: str = None):
        if api_key is None:
            api_key = getattr(settings, "MASSIVE_API_KEY", None)

        if not api_key:
            raise DataSourceError("MASSIVE_API_KEY is required. Set in environment variables.")

        self.api_key = api_key
        self.client = RESTClient(api_key=api_key)
        self._last_request_time = None

    def _apply_rate_limit(self):
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < RATE_LIMIT_DELAY_SECONDS:
                sleep_time = RATE_LIMIT_DELAY_SECONDS - elapsed
                time.sleep(sleep_time)
        self._last_request_time = time.time()

    def fetch_historical_prices(self, ticker: str, start_date: date, end_date: date) -> List[dict]:
        self._apply_rate_limit()
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
                raise DataNotFoundError(f"Ticker '{ticker}' not found on Massive.com") from e
            raise DataSourceError(f"Failed to fetch data from Massive.com: {str(e)}") from e

    def fetch_grouped_daily(self, date: date) -> dict:
        self._apply_rate_limit()
        try:
            aggs = self.client.get_grouped_daily_aggs(
                date=date.strftime("%Y-%m-%d"),
                adjusted=True,
            )

            results = {}
            for agg in aggs:
                if not hasattr(agg, "ticker"):
                    continue

                try:
                    results[agg.ticker] = self._transform_result(agg.ticker, agg)
                except (AttributeError, ValueError):
                    continue

            return results

        except Exception as e:
            raise DataSourceError(f"Failed to fetch grouped daily data: {str(e)}") from e

    def _transform_result(self, ticker: str, agg) -> dict:
        if not hasattr(agg, "timestamp"):
            raise DataSourceError("Missing timestamp in response")

        timestamp = datetime.fromtimestamp(agg.timestamp / 1000, tz=timezone.utc)

        return {
            "ticker": ticker,
            "timestamp": timestamp,
            "open": Decimal(str(agg.open)),
            "high": Decimal(str(agg.high)),
            "low": Decimal(str(agg.low)),
            "close": Decimal(str(agg.close)),
            "volume": Decimal(str(agg.volume)) if agg.volume else None,
        }
