"""
External data source stub file.

This file is kept as a placeholder for future data source implementations.

CURRENT STATUS: No external data sources implemented.

ALTERNATIVE APPROACHES:
1. Add funds manually via Django admin
2. Use: python manage.py add_sample_funds
3. Wait for official data source implementations:
   - Alpha Vantage (official API with free tier)
   - massive.com (official API with free tier)
   - Finnhub (official API with free tier)

For now, use the Django admin to add funds manually:
http://localhost:8000/admin/feefifofunds/fund/
"""

from datetime import date
from typing import List

from .base import BaseDataSource, DataSourceError
from .dto import FundDataDTO, HoldingDataDTO, PerformanceDataDTO


class ExampleDataSource(BaseDataSource):
    """
    Example data source stub.

    This is a placeholder for future data source implementations.
    No external data sources are currently implemented.

    Use Django admin to add funds manually.
    """

    name = "example_source"
    display_name = "Example Source (Not Implemented)"
    base_url = "https://api.example.com"
    requires_api_key = True
    rate_limit_requests = 0  # Not implemented
    rate_limit_period = 0

    def __init__(self, api_key=None):
        super().__init__(api_key)
        """Not implemented - raises error on initialization."""
        raise DataSourceError(
            "No external data sources are currently implemented. "
            "Please add funds manually via Django admin: /admin/feefifofunds/fund/ "
            "or use: python manage.py add_sample_funds"
        )

    def fetch_fund_info(self, ticker: str) -> FundDataDTO:
        """Not implemented."""
        raise DataSourceError("No data sources implemented")

    def fetch_historical_prices(
        self, ticker: str, start_date: date, end_date: date, interval: str = "1d"
    ) -> List[PerformanceDataDTO]:
        """Not implemented."""
        raise DataSourceError("No data sources implemented")

    def fetch_holdings(self, ticker: str) -> List[HoldingDataDTO]:
        """Not implemented."""
        raise DataSourceError("No data sources implemented")
