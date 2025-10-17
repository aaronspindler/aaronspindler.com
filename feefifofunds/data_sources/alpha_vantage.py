"""
Alpha Vantage API data source.

Best for: ETF fundamentals and company data
Free Tier: 500 requests/day, 5 calls/minute
API Key: Required (free at alphavantage.co)
"""

import logging
import os
import time
from datetime import date
from decimal import Decimal
from typing import Optional

import requests

from .base import BaseDataSource
from .dto import FundDataDTO

logger = logging.getLogger(__name__)


class AlphaVantageSource(BaseDataSource):
    """
    Fetch ETF data from Alpha Vantage API.

    Requires API key (free at https://www.alphavantage.co/support/#api-key)
    Rate Limit: 5 calls/minute (free tier)

    Supports:
    - ETFs (US primarily)
    - Basic fund information

    Does NOT support:
    - Mutual funds
    - Canadian funds (limited data)
    """

    BASE_URL = "https://www.alphavantage.co/query"
    DEFAULT_RATE_LIMIT = 12  # seconds between calls (5 per minute)

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Alpha Vantage source.

        Args:
            api_key: Alpha Vantage API key (or set ALPHA_VANTAGE_API_KEY env var)
        """
        super().__init__(**kwargs)

        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")

        if not self.api_key:
            logger.warning(
                "[AlphaVantage] No API key provided. " "Get free key at https://www.alphavantage.co/support/#api-key"
            )

        # Set rate limiting to comply with free tier (5 calls/minute)
        self._rate_limit_delay = self.DEFAULT_RATE_LIMIT
        self._last_request_time = 0

    def fetch_fund(self, ticker: str) -> Optional[FundDataDTO]:
        """
        Fetch fund data from Alpha Vantage.

        Args:
            ticker: Fund ticker (US ETFs primarily)

        Returns:
            FundDataDTO if found, None otherwise
        """
        if not self.api_key:
            logger.error("[AlphaVantage] API key required")
            return None

        # Check cache first
        cached = self._get_from_cache(ticker)
        if cached:
            return cached

        # Apply rate limiting
        self._enforce_rate_limit()

        try:
            logger.info(f"[AlphaVantage] Fetching {ticker}")

            # Fetch overview data
            params = {"function": "OVERVIEW", "symbol": ticker, "apikey": self.api_key}

            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if "Error Message" in data:
                logger.warning(f"[AlphaVantage] {data['Error Message']}")
                return None

            if "Note" in data:
                logger.warning(f"[AlphaVantage] Rate limit message: {data['Note']}")
                return None

            # Check if we got data
            if not data or "Symbol" not in data:
                logger.warning(f"[AlphaVantage] No data found for {ticker}")
                return None

            # Parse data
            fund_data = self._parse_alpha_vantage_data(ticker, data)

            # Cache and return
            if fund_data:
                self._save_to_cache(ticker, fund_data)

            return fund_data

        except requests.RequestException as e:
            logger.error(f"[AlphaVantage] Request error for {ticker}: {e}")
            return None
        except Exception as e:
            logger.error(f"[AlphaVantage] Error fetching {ticker}: {e}")
            return None

    def _parse_alpha_vantage_data(self, ticker: str, data: dict) -> FundDataDTO:
        """Parse Alpha Vantage API response into FundDataDTO."""
        # Basic info
        name = data.get("Name") or ticker
        description = data.get("Description", "")

        # Determine fund type
        asset_type = data.get("AssetType", "")
        fund_type = "ETF" if asset_type == "ETF" else "ETF"

        # Provider/issuer
        provider_name = data.get("Issuer") or self._guess_provider_from_name(name)

        # MER/Expense Ratio - Alpha Vantage doesn't always provide this
        mer = None

        # Classification
        asset_class = self._map_sector_to_asset_class(data.get("Sector"))

        # Geographic focus
        exchange = data.get("Exchange", "")
        geographic_focus = "US" if any(x in exchange for x in ["NYSE", "NASDAQ", "AMEX"]) else None

        # Performance data - Alpha Vantage OVERVIEW doesn't include returns
        # Would need separate TIME_SERIES calls which would use more API credits

        # Fund details
        market_cap = data.get("MarketCapitalization")
        aum = None
        if market_cap:
            try:
                # Convert to millions
                aum = Decimal(str(int(market_cap) / 1_000_000))
            except (ValueError, TypeError):
                pass

        # Data source URL
        data_source_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}"

        return FundDataDTO(
            ticker=ticker,
            name=name,
            fund_type=fund_type,
            provider_name=provider_name,
            mer=mer,
            asset_class=asset_class,
            geographic_focus=geographic_focus,
            description=description[:500] if description else None,
            aum=aum,
            data_source_url=data_source_url,
            last_data_update=date.today(),
            source_name="AlphaVantage",
        )

    def _guess_provider_from_name(self, name: str) -> Optional[str]:
        """Guess provider from fund name."""
        providers_map = {
            "vanguard": "Vanguard",
            "ishares": "iShares",
            "spdr": "State Street Global Advisors",
            "invesco": "Invesco",
            "schwab": "Charles Schwab",
            "proshares": "ProShares",
            "direxion": "Direxion",
        }

        name_lower = name.lower()
        for key, provider in providers_map.items():
            if key in name_lower:
                return provider

        return None

    def _map_sector_to_asset_class(self, sector: Optional[str]) -> Optional[str]:
        """Map Alpha Vantage sector to asset class."""
        if not sector:
            return None

        sector_lower = sector.lower()

        if any(word in sector_lower for word in ["equity", "stock"]):
            return "EQUITY"
        elif any(word in sector_lower for word in ["bond", "fixed income"]):
            return "BONDS"
        elif "real estate" in sector_lower:
            return "REAL_ESTATE"
        elif "commodity" in sector_lower:
            return "COMMODITIES"
        else:
            return "EQUITY"

    def _enforce_rate_limit(self):
        """Enforce rate limiting (5 calls/minute for free tier)."""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time

        if time_since_last_request < self._rate_limit_delay:
            sleep_time = self._rate_limit_delay - time_since_last_request
            logger.debug(f"[AlphaVantage] Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def supports_fund_type(self, fund_type: str) -> bool:
        """Alpha Vantage primarily supports ETFs."""
        return fund_type == "ETF"

    def get_source_info(self) -> dict:
        """Get information about Alpha Vantage source."""
        info = super().get_source_info()
        info.update(
            {
                "description": "Alpha Vantage API",
                "best_for": "ETF fundamentals (US)",
                "requires_api_key": True,
                "api_key_set": bool(self.api_key),
                "free_tier_limit": "500 requests/day, 5 calls/minute",
                "get_api_key": "https://www.alphavantage.co/support/#api-key",
            }
        )
        return info
