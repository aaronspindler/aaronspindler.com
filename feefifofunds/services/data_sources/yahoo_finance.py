"""
Yahoo Finance data source integration.

Uses yfinance library to fetch fund data from Yahoo Finance.
Free tier with no API key required.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

import yfinance as yf
from django.utils import timezone

from .base import BaseDataSource, DataNotFoundError, DataSourceError
from .dto import FundDataDTO, HoldingDataDTO, PerformanceDataDTO


class YahooFinance(BaseDataSource):
    """
    Yahoo Finance data source implementation.

    Free data source for stocks, ETFs, and mutual funds.
    No API key required.

    Rate Limits:
    - ~2000 requests per hour (unofficial)
    - ~48,000 requests per day (unofficial)

    Note: Yahoo Finance doesn't have official rate limits,
    but we implement conservative limits to be respectful.
    """

    name = "yahoo_finance"
    display_name = "Yahoo Finance"
    base_url = "https://query1.finance.yahoo.com"
    requires_api_key = False
    rate_limit_requests = 2000
    rate_limit_period = 3600  # 1 hour

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Yahoo Finance data source.

        Args:
            api_key: Not required for Yahoo Finance
        """
        super().__init__(api_key=api_key)

        # Update data source model with capabilities
        self.data_source_model.supports_historical_data = True
        self.data_source_model.supports_realtime_data = True
        self.data_source_model.supports_holdings = True
        self.data_source_model.supports_fundamentals = True
        self.data_source_model.is_free = True
        self.data_source_model.save(
            update_fields=[
                "supports_historical_data",
                "supports_realtime_data",
                "supports_holdings",
                "supports_fundamentals",
                "is_free",
            ]
        )

    def fetch_fund_info(self, ticker: str) -> FundDataDTO:
        """
        Fetch fund information from Yahoo Finance.

        Args:
            ticker: Fund ticker symbol (e.g., 'SPY', 'VTSAX')

        Returns:
            FundDataDTO with fund information

        Raises:
            DataNotFoundError: If fund not found
            DataSourceError: If fetch fails
        """
        try:
            # Create yfinance Ticker object
            fund = yf.Ticker(ticker)

            # Get fund info
            info = fund.info

            if not info or "symbol" not in info:
                raise DataNotFoundError(f"Fund {ticker} not found on Yahoo Finance")

            # Determine fund type
            quote_type = info.get("quoteType", "").upper()
            fund_type_map = {
                "ETF": "ETF",
                "MUTUALFUND": "MUTUAL",
                "EQUITY": "ETF",  # Assume stock-like is ETF for now
            }
            fund_type = fund_type_map.get(quote_type, "OTHER")

            # Determine asset class from category
            category = info.get("category", "")
            asset_class = self._map_category_to_asset_class(category)

            # Extract data
            fund_data = FundDataDTO(
                ticker=ticker.upper(),
                name=info.get("longName") or info.get("shortName") or ticker,
                fund_type=fund_type,
                asset_class=asset_class,
                category=category,
                description=info.get("longBusinessSummary", ""),
                inception_date=self._parse_date(info.get("fundInceptionDate")),
                issuer=info.get("fundFamily", ""),
                expense_ratio=self._to_decimal(info.get("annualReportExpenseRatio"), scale=10000),
                management_fee=self._to_decimal(info.get("managementFee")),
                current_price=self._to_decimal(info.get("regularMarketPrice") or info.get("navPrice")),
                previous_close=self._to_decimal(info.get("previousClose")),
                currency=info.get("currency", "USD"),
                aum=self._to_decimal(info.get("totalAssets"), divide_by=1000000),  # Convert to millions
                avg_volume=info.get("averageVolume"),
                exchange=info.get("exchange", ""),
                website=info.get("website", ""),
                isin=info.get("isin", ""),
                source="yahoo_finance",
                fetched_at=timezone.now(),
            )

            self.record_request(success=True)
            return fund_data

        except Exception as e:
            self.record_request(success=False, error_message=str(e))
            if "404" in str(e) or "not found" in str(e).lower():
                raise DataNotFoundError(f"Fund {ticker} not found: {e}")
            raise DataSourceError(f"Failed to fetch fund info: {e}")

    def fetch_historical_prices(
        self, ticker: str, start_date: date, end_date: date, interval: str = "1d"
    ) -> List[PerformanceDataDTO]:
        """
        Fetch historical price data from Yahoo Finance.

        Args:
            ticker: Fund ticker symbol
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval (1d, 1wk, 1mo, 3mo)

        Returns:
            List of PerformanceDataDTO objects

        Raises:
            DataNotFoundError: If no data available
            DataSourceError: If fetch fails
        """
        try:
            # Create yfinance Ticker object
            fund = yf.Ticker(ticker)

            # Map interval to our internal format
            interval_map = {"1d": "1D", "1wk": "1W", "1mo": "1M", "3mo": "1Q"}
            internal_interval = interval_map.get(interval, "1D")

            # Download historical data
            hist = fund.history(start=start_date, end=end_date, interval=interval, auto_adjust=False)

            if hist.empty:
                raise DataNotFoundError(f"No historical data found for {ticker}")

            # Convert to PerformanceDataDTO list
            performance_data = []
            for idx, row in hist.iterrows():
                perf = PerformanceDataDTO(
                    ticker=ticker.upper(),
                    date=idx.date(),
                    open_price=self._to_decimal(row.get("Open")),
                    high_price=self._to_decimal(row.get("High")),
                    low_price=self._to_decimal(row.get("Low")),
                    close_price=self._to_decimal(row.get("Close")),
                    adjusted_close=self._to_decimal(row.get("Adj Close")),
                    volume=int(row.get("Volume", 0)) if row.get("Volume") else None,
                    dividend=self._to_decimal(row.get("Dividends")),
                    split_ratio=self._to_decimal(row.get("Stock Splits")),
                    interval=internal_interval,
                    source="yahoo_finance",
                    fetched_at=timezone.now(),
                )
                performance_data.append(perf)

            self.record_request(success=True)
            return performance_data

        except Exception as e:
            self.record_request(success=False, error_message=str(e))
            if "No data found" in str(e):
                raise DataNotFoundError(f"No historical data for {ticker}: {e}")
            raise DataSourceError(f"Failed to fetch historical prices: {e}")

    def fetch_holdings(self, ticker: str) -> List[HoldingDataDTO]:
        """
        Fetch fund holdings from Yahoo Finance.

        Args:
            ticker: Fund ticker symbol

        Returns:
            List of HoldingDataDTO objects

        Raises:
            DataNotFoundError: If holdings not available
            DataSourceError: If fetch fails
        """
        try:
            # Create yfinance Ticker object
            fund = yf.Ticker(ticker)

            # Get holdings data
            # Note: Yahoo Finance has limited holdings data
            # For ETFs, we can get major holdings
            holdings_data = []

            # Try to get major holders (top holdings)
            try:
                info = fund.info
                if "holdings" in info:
                    holdings_list = info["holdings"]
                    if holdings_list and isinstance(holdings_list, list):
                        for holding in holdings_list[:50]:  # Top 50 holdings
                            holdings_data.append(
                                HoldingDataDTO(
                                    ticker=holding.get("symbol", ""),
                                    name=holding.get("holdingName", ""),
                                    weight=self._to_decimal(holding.get("holdingPercent"), scale=100) or Decimal("0"),
                                    sector=holding.get("sector", ""),
                                    as_of_date=date.today(),
                                    source="yahoo_finance",
                                    fetched_at=timezone.now(),
                                )
                            )
            except (KeyError, AttributeError, TypeError):
                pass

            # Alternative: Try fund_holding_info (for some mutual funds)
            if not holdings_data:
                try:
                    if hasattr(fund, "fund_holding_info"):
                        holdings_df = fund.fund_holding_info
                        if holdings_df is not None and not holdings_df.empty:
                            for idx, row in holdings_df.iterrows():
                                holdings_data.append(
                                    HoldingDataDTO(
                                        ticker=row.get("Symbol", idx),
                                        name=row.get("Holding", ""),
                                        weight=self._to_decimal(row.get("% Assets")) or Decimal("0"),
                                        sector=row.get("Sector", ""),
                                        as_of_date=date.today(),
                                        source="yahoo_finance",
                                        fetched_at=timezone.now(),
                                    )
                                )
                except Exception:
                    pass

            if not holdings_data:
                raise DataNotFoundError(f"Holdings data not available for {ticker}")

            self.record_request(success=True)
            return holdings_data

        except DataNotFoundError:
            raise
        except Exception as e:
            self.record_request(success=False, error_message=str(e))
            raise DataSourceError(f"Failed to fetch holdings: {e}")

    # Helper methods

    def _to_decimal(self, value: any, scale: int = 1, divide_by: int = 1) -> Optional[Decimal]:
        """
        Convert value to Decimal with proper handling.

        Args:
            value: Value to convert
            scale: Multiply by this (e.g., 10000 to convert 0.0003 to 3)
            divide_by: Divide by this (e.g., 1000000 to convert to millions)

        Returns:
            Decimal value or None
        """
        if value is None or value == "":
            return None

        try:
            decimal_value = Decimal(str(value))
            if scale != 1:
                decimal_value = decimal_value * Decimal(str(scale))
            if divide_by != 1:
                decimal_value = decimal_value / Decimal(str(divide_by))
            return decimal_value
        except (ValueError, TypeError, ArithmeticError):
            return None

    def _parse_date(self, timestamp: any) -> Optional[date]:
        """
        Parse timestamp to date.

        Args:
            timestamp: Unix timestamp or date string

        Returns:
            date object or None
        """
        if timestamp is None:
            return None

        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp).date()
            elif isinstance(timestamp, str):
                return datetime.fromisoformat(timestamp).date()
            elif isinstance(timestamp, datetime):
                return timestamp.date()
            elif isinstance(timestamp, date):
                return timestamp
        except (ValueError, TypeError, OSError):
            pass

        return None

    def _map_category_to_asset_class(self, category: str) -> str:
        """
        Map Yahoo Finance category to our asset class.

        Args:
            category: Yahoo Finance category string

        Returns:
            Asset class code (EQUITY, BOND, MIXED, etc.)
        """
        category_lower = category.lower()

        if any(word in category_lower for word in ["equity", "stock", "growth", "value", "blend"]):
            return "EQUITY"
        elif any(word in category_lower for word in ["bond", "fixed income", "income"]):
            return "BOND"
        elif any(word in category_lower for word in ["balanced", "allocation", "mixed"]):
            return "MIXED"
        elif "money market" in category_lower:
            return "MM"
        elif any(word in category_lower for word in ["commodity", "gold", "silver"]):
            return "COMMODITY"
        elif any(word in category_lower for word in ["real estate", "reit"]):
            return "REIT"
        else:
            return "EQUITY"  # Default to equity

    def fetch_latest_price(self, ticker: str) -> Optional[Decimal]:
        """
        Fetch just the latest price for a fund (quick operation).

        Args:
            ticker: Fund ticker symbol

        Returns:
            Current price as Decimal or None

        Raises:
            DataSourceError: If fetch fails
        """
        try:
            fund = yf.Ticker(ticker)
            info = fund.info

            price = info.get("regularMarketPrice") or info.get("navPrice") or info.get("previousClose")

            if price:
                self.record_request(success=True)
                return Decimal(str(price))

            self.record_request(success=False, error_message="Price not available")
            return None

        except Exception as e:
            self.record_request(success=False, error_message=str(e))
            raise DataSourceError(f"Failed to fetch latest price: {e}")

    def fetch_bulk_quotes(self, tickers: List[str]) -> dict[str, Decimal]:
        """
        Fetch current prices for multiple tickers in one request.

        More efficient than fetching one at a time.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to current price

        Raises:
            DataSourceError: If fetch fails
        """
        try:
            if not tickers:
                return {}

            # Download data for all tickers
            data = yf.download(tickers, period="1d", progress=False, show_errors=False)

            prices = {}
            if len(tickers) == 1:
                # Single ticker returns different structure
                if not data.empty and "Close" in data.columns:
                    prices[tickers[0]] = Decimal(str(data["Close"].iloc[-1]))
            else:
                # Multiple tickers
                if not data.empty and "Close" in data.columns:
                    close_prices = data["Close"].iloc[-1]
                    for ticker in tickers:
                        if ticker in close_prices:
                            prices[ticker] = Decimal(str(close_prices[ticker]))

            self.record_request(success=True)
            return prices

        except Exception as e:
            self.record_request(success=False, error_message=str(e))
            raise DataSourceError(f"Failed to fetch bulk quotes: {e}")

    def get_fund_profile(self, ticker: str) -> dict:
        """
        Get complete fund profile with all available data.

        Returns raw Yahoo Finance info dict for debugging/inspection.

        Args:
            ticker: Fund ticker symbol

        Returns:
            Dictionary with all available fund data
        """
        try:
            fund = yf.Ticker(ticker)
            info = fund.info
            self.record_request(success=True)
            return info
        except Exception as e:
            self.record_request(success=False, error_message=str(e))
            raise DataSourceError(f"Failed to fetch fund profile: {e}")
