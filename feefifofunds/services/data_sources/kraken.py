import time
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List

from .base import BaseDataSource, DataNotFoundError, DataSourceError

MAX_CANDLES = 720
RATE_LIMIT_DELAY_SECONDS = 1.0


class KrakenDataSource(BaseDataSource):
    name = "kraken"
    display_name = "Kraken"
    base_url = "https://api.kraken.com/0/public"
    requires_api_key = False
    max_candles = MAX_CANDLES
    rate_limit_delay = RATE_LIMIT_DELAY_SECONDS

    INTERVAL_MAP = {
        1: 1,
        5: 5,
        15: 15,
        30: 30,
        60: 60,
        240: 240,
        1440: 1440,
        10080: 10080,
        21600: 21600,
    }

    def __init__(self, api_key: str = None):
        super().__init__(api_key)
        self._last_request_time = None

    def _apply_rate_limit(self):
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def fetch_historical_prices(
        self,
        pair: str,
        start_date: date,
        end_date: date,
        interval_minutes: int = 1440,
    ) -> List[dict]:
        if interval_minutes not in self.INTERVAL_MAP:
            valid_intervals = ", ".join(str(i) for i in sorted(self.INTERVAL_MAP.keys()))
            raise DataSourceError(f"Invalid interval: {interval_minutes}. Valid intervals: {valid_intervals}")

        self._apply_rate_limit()

        url = f"{self.base_url}/OHLC"
        params = {
            "pair": pair,
            "interval": self.INTERVAL_MAP[interval_minutes],
        }

        if start_date:
            since_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp())
            params["since"] = since_timestamp

        data = self._make_request(url, params)

        if "error" in data and data["error"]:
            error_messages = ", ".join(data["error"])
            if "Unknown asset pair" in error_messages:
                raise DataNotFoundError(f"Unknown asset pair: {pair}")
            raise DataSourceError(f"Kraken API error: {error_messages}")

        if "result" not in data:
            raise DataNotFoundError(f"No data returned for pair: {pair}")

        ohlc_data = None
        for key, value in data["result"].items():
            if key != "last" and isinstance(value, list):
                ohlc_data = value
                break

        if not ohlc_data:
            return []

        return self._transform_results(pair, ohlc_data, interval_minutes)

    def _transform_results(self, pair: str, ohlc_data: list, interval_minutes: int) -> List[dict]:
        results = []

        for candle in ohlc_data[:-1]:
            if len(candle) < 8:
                continue

            try:
                timestamp = datetime.fromtimestamp(int(candle[0]), tz=timezone.utc)

                results.append(
                    {
                        "pair": pair,
                        "timestamp": timestamp,
                        "open": Decimal(str(candle[1])),
                        "high": Decimal(str(candle[2])),
                        "low": Decimal(str(candle[3])),
                        "close": Decimal(str(candle[4])),
                        "volume": Decimal(str(candle[6])),
                        "trade_count": int(candle[7]),
                        "interval_minutes": interval_minutes,
                    }
                )
            except (ValueError, IndexError, TypeError):
                continue

        return results
