"""
Yahoo Finance data source - REMOVED.

Yahoo Finance data fetching has been removed due to unreliable API access
and aggressive rate limiting. Yahoo does not provide an official API, and
the unofficial yfinance library is frequently blocked.

ALTERNATIVE APPROACHES:
1. Add funds manually via Django admin
2. Use CSV import (future implementation)
3. Use alternative data sources when implemented:
   - Alpha Vantage (official API with free tier)
   - Polygon.io (official API with free tier)
   - Finnhub (official API with free tier)

For now, use the Django admin to add funds manually:
http://localhost:8000/admin/feefifofunds/fund/
"""

from datetime import date
from typing import List

from .base import BaseDataSource, DataSourceError
from .dto import FundDataDTO, HoldingDataDTO, PerformanceDataDTO


class YahooFinance(BaseDataSource):
    """
    Yahoo Finance data source - STUB ONLY.

    This implementation has been disabled due to Yahoo Finance's aggressive
    rate limiting and lack of official API support.

    Use Django admin to add funds manually instead.
    """

    name = "yahoo_finance"
    display_name = "Yahoo Finance (Disabled)"
    base_url = "https://query1.finance.yahoo.com"
    requires_api_key = False
    rate_limit_requests = 0  # Disabled
    rate_limit_period = 0

    def __init__(self, api_key=None):
        """Disabled - raises error on initialization."""
        raise DataSourceError(
            "Yahoo Finance data source is disabled due to unreliable API access. "
            "Please add funds manually via Django admin: /admin/feefifofunds/fund/ "
            "or use: python manage.py add_sample_funds"
        )

    def fetch_fund_info(self, ticker: str) -> FundDataDTO:
        """Disabled."""
        raise DataSourceError("Yahoo Finance data source is disabled")

    def fetch_historical_prices(
        self, ticker: str, start_date: date, end_date: date, interval: str = "1d"
    ) -> List[PerformanceDataDTO]:
        """Disabled."""
        raise DataSourceError("Yahoo Finance data source is disabled")

    def fetch_holdings(self, ticker: str) -> List[HoldingDataDTO]:
        """Disabled."""
        raise DataSourceError("Yahoo Finance data source is disabled")
