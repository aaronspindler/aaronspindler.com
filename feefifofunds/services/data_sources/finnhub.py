"""
Finnhub Data Source Implementation.

Provides financial market data including stocks and crypto:
- Rate Limit: 60 calls/minute (free tier)
- Historical Data: Available with OHLC endpoint
- Real-time Data: WebSocket available
- Crypto Support: Yes

API Documentation: https://finnhub.io/docs/api
Client Library: https://github.com/Finnhub-Stock-API/finnhub-python
"""

from datetime import date, datetime, time
from decimal import Decimal
from typing import List

import finnhub
from django.conf import settings

from .base import DataNotFoundError, DataSourceError


class FinnhubDataSource:
    name = "finnhub"
    display_name = "Finnhub"
    requires_api_key = True

    def __init__(self, api_key: str = None):
        if api_key is None:
            api_key = getattr(settings, "FINNHUB_API_KEY", None)

        if not api_key:
            raise DataSourceError("FINNHUB_API_KEY is required. Set in environment variables.")

        self.api_key = api_key
        self.client = finnhub.Client(api_key=api_key)

    def fetch_historical_prices(self, ticker: str, start_date: date, end_date: date) -> List[dict]:
        """
        Fetch historical price data from Finnhub.

        Args:
            ticker: Stock/Crypto ticker (e.g., AAPL, BINANCE:BTCUSDT)
            start_date: Start date
            end_date: End date

        Returns:
            List of price dictionaries
        """
        start_timestamp = int(datetime.combine(start_date, time.min).timestamp())
        end_timestamp = int(datetime.combine(end_date, time.max).timestamp())

        try:
            data = self.client.stock_candles(ticker, "D", start_timestamp, end_timestamp)

            if data.get("s") == "no_data":
                return []

            if data.get("s") != "ok":
                raise DataNotFoundError(f"Ticker '{ticker}' not found or no data available")

            return self._transform_results(ticker, data)

        except DataNotFoundError:
            raise
        except Exception as e:
            raise DataSourceError(f"Failed to fetch data from Finnhub: {str(e)}")

    def _transform_results(self, ticker: str, data: dict) -> List[dict]:
        """Transform Finnhub response to standard format."""
        timestamps = data.get("t", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        closes = data.get("c", [])
        volumes = data.get("v", [])

        if not timestamps:
            return []

        results = []
        for i in range(len(timestamps)):
            timestamp = datetime.fromtimestamp(timestamps[i])

            results.append(
                {
                    "ticker": ticker,
                    "timestamp": timestamp,
                    "open": Decimal(str(opens[i])),
                    "high": Decimal(str(highs[i])),
                    "low": Decimal(str(lows[i])),
                    "close": Decimal(str(closes[i])),
                    "volume": Decimal(str(volumes[i])) if volumes and volumes[i] else None,
                }
            )

        return results
