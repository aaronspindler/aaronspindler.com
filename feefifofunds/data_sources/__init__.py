"""
Data source package for fetching fund data from multiple providers.

Supports:
- Yahoo Finance (ETFs via yfinance)
- Alpha Vantage API (ETFs)
- CSV import (manual data)
- Future: Morningstar scraper (mutual funds)
"""

from .alpha_vantage import AlphaVantageSource
from .base import BaseDataSource
from .csv_source import CSVSource
from .dto import FundDataDTO
from .manager import DataSourceManager
from .yahoo_finance import YahooFinanceSource

__all__ = [
    "BaseDataSource",
    "FundDataDTO",
    "YahooFinanceSource",
    "AlphaVantageSource",
    "CSVSource",
    "DataSourceManager",
]
