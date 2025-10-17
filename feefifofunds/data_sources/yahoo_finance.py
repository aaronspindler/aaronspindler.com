"""
Yahoo Finance data source implementation using yfinance library.

Best for: ETF data (Canadian and US)
Free: Yes (no API key required)
Rate Limit: Built into yfinance library
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from .base import BaseDataSource
from .dto import FundDataDTO

logger = logging.getLogger(__name__)

try:
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance library not installed. Install with: pip install yfinance")


class YahooFinanceSource(BaseDataSource):
    """
    Fetch ETF data from Yahoo Finance using the yfinance library.

    Supports:
    - Canadian ETFs (ticker.TO)
    - US ETFs (ticker without suffix)
    - Basic fund information, MER, performance

    Does NOT support:
    - Mutual funds (not typically on Yahoo Finance)
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rate_limit_delay = 0.5  # 500ms delay between requests

        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance library is required. Install with: pip install yfinance")

    def fetch_fund(self, ticker: str) -> Optional[FundDataDTO]:
        """
        Fetch fund data from Yahoo Finance.

        Args:
            ticker: Fund ticker (e.g., "VFV.TO" for Canadian, "VOO" for US)

        Returns:
            FundDataDTO if found, None otherwise
        """
        # Check cache first
        cached = self._get_from_cache(ticker)
        if cached:
            return cached

        try:
            logger.info(f"[YahooFinance] Fetching {ticker}")

            # Fetch ticker data
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            # Check if ticker exists and has data
            if not info or "symbol" not in info:
                logger.warning(f"[YahooFinance] No data found for {ticker}")
                return None

            # Extract data
            fund_data = self._parse_yahoo_data(ticker, info)

            # Try to fetch historical performance
            try:
                hist = ticker_obj.history(period="1y")
                if not hist.empty:
                    # Calculate 1-year return
                    start_price = hist["Close"].iloc[0]
                    end_price = hist["Close"].iloc[-1]
                    one_year_return = ((end_price - start_price) / start_price) * 100
                    fund_data.one_year_return = Decimal(str(round(one_year_return, 2)))
            except Exception as e:
                logger.debug(f"[YahooFinance] Could not fetch historical data for {ticker}: {e}")

            # Cache and return
            if fund_data:
                self._save_to_cache(ticker, fund_data)

            return fund_data

        except Exception as e:
            logger.error(f"[YahooFinance] Error fetching {ticker}: {e}")
            return None

    def _parse_yahoo_data(self, ticker: str, info: dict) -> FundDataDTO:
        """Parse Yahoo Finance info dict into FundDataDTO."""
        # Determine fund type (Yahoo Finance primarily has ETFs)
        quote_type = info.get("quoteType", "")
        fund_type = "ETF" if quote_type == "ETF" else "ETF"  # Default to ETF

        # Extract basic info
        name = info.get("longName") or info.get("shortName") or ticker
        description = info.get("longBusinessSummary", "")

        # Extract MER (expense ratio) - this is critical
        mer = None
        if "annualReportExpenseRatio" in info and info["annualReportExpenseRatio"]:
            # Yahoo returns this as a decimal (0.08 for 0.08%)
            mer = Decimal(str(info["annualReportExpenseRatio"] * 100))
        elif "expenseRatio" in info and info["expenseRatio"]:
            mer = Decimal(str(info["expenseRatio"] * 100))

        # Determine provider from ticker or name
        provider_name = self._guess_provider(ticker, name)

        # Determine asset class
        asset_class = self._map_category_to_asset_class(info.get("category"))

        # Determine geographic focus
        geographic_focus = self._guess_geographic_focus(ticker, name, description)

        # Extract AUM (total assets)
        aum = None
        if "totalAssets" in info and info["totalAssets"]:
            # Convert to millions
            aum = Decimal(str(info["totalAssets"] / 1_000_000))

        # Extract inception date
        inception_date = None
        if "fundInceptionDate" in info and info["fundInceptionDate"]:
            try:
                inception_date = datetime.fromtimestamp(info["fundInceptionDate"]).date()
            except (ValueError, TypeError):
                pass

        # Build data source URL
        data_source_url = f"https://finance.yahoo.com/quote/{ticker}"

        return FundDataDTO(
            ticker=ticker,
            name=name,
            fund_type=fund_type,
            provider_name=provider_name,
            mer=mer,
            asset_class=asset_class,
            geographic_focus=geographic_focus,
            description=description[:500] if description else None,  # Truncate long descriptions
            inception_date=inception_date,
            aum=aum,
            data_source_url=data_source_url,
            last_data_update=date.today(),
            source_name="YahooFinance",
        )

    def _guess_provider(self, ticker: str, name: str) -> Optional[str]:
        """Guess the fund provider from ticker or name."""
        # Common Canadian/US providers
        providers_map = {
            "vanguard": "Vanguard",
            "ishares": "iShares",
            "blackrock": "iShares",
            "spdr": "State Street Global Advisors",
            "bmo": "BMO",
            "td": "TD Asset Management",
            "rbc": "RBC",
            "horizons": "Horizons ETFs",
            "invesco": "Invesco",
            "schwab": "Charles Schwab",
        }

        combined_text = f"{ticker} {name}".lower()

        for key, provider in providers_map.items():
            if key in combined_text:
                return provider

        return "Unknown"

    def _map_category_to_asset_class(self, category: Optional[str]) -> Optional[str]:
        """Map Yahoo Finance category to our asset class."""
        if not category:
            return None

        category_lower = category.lower()

        if any(word in category_lower for word in ["equity", "stock", "large", "mid", "small", "growth", "value"]):
            return "EQUITY"
        elif any(word in category_lower for word in ["bond", "fixed income", "government", "corporate"]):
            return "BONDS"
        elif "balanced" in category_lower or "allocation" in category_lower:
            return "BALANCED"
        elif "real estate" in category_lower or "reit" in category_lower:
            return "REAL_ESTATE"
        elif "commodity" in category_lower or "commodities" in category_lower:
            return "COMMODITIES"
        elif "money market" in category_lower:
            return "MONEY_MARKET"
        else:
            return "EQUITY"  # Default to equity

    def _guess_geographic_focus(self, ticker: str, name: str, description: str) -> Optional[str]:
        """Guess geographic focus from ticker, name, and description."""
        combined_text = f"{ticker} {name} {description}".lower()

        # Canadian indicators
        if ".to" in ticker.lower() or any(word in combined_text for word in ["canadian", "canada", "tsx"]):
            return "CANADIAN"

        # US indicators
        if any(word in combined_text for word in ["s&p 500", "u.s.", "united states", "american", "nasdaq"]):
            return "US"

        # International
        if any(
            word in combined_text
            for word in ["international", "eafe", "developed markets", "ex-us", "ex-north america"]
        ):
            return "INTERNATIONAL"

        # Emerging markets
        if any(word in combined_text for word in ["emerging", "em ", "developing"]):
            return "EMERGING"

        # Global
        if any(word in combined_text for word in ["global", "world", "all-country"]):
            return "GLOBAL"

        # Default based on ticker suffix
        if ".to" in ticker.lower():
            return "CANADIAN"
        else:
            return "US"

    def supports_fund_type(self, fund_type: str) -> bool:
        """Yahoo Finance primarily supports ETFs."""
        return fund_type == "ETF"

    def get_source_info(self) -> dict:
        """Get information about Yahoo Finance source."""
        info = super().get_source_info()
        info.update(
            {
                "description": "Yahoo Finance API via yfinance library",
                "best_for": "ETF data (Canadian .TO and US)",
                "requires_api_key": False,
                "supports_search": False,
            }
        )
        return info
