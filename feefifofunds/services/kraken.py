import csv
from datetime import datetime
from datetime import timezone as dt_timezone
from decimal import Decimal
from typing import Iterator

from django.db import transaction

from feefifofunds.models import Asset


class KrakenPairParser:
    QUOTE_CURRENCIES = [
        # Z-prefixed versions (check these first for longer matches)
        "ZUSD",
        "ZEUR",
        "ZGBP",
        "ZJPY",
        "ZCAD",
        "ZCHF",
        "ZAUD",
        "ZAED",
        # Regular versions
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "CAD",
        "CHF",
        "AUD",
        "AED",
        "XBT",
        "ETH",
        "DAI",
        "DOT",
        "POL",
    ]

    KRAKEN_TICKER_MAPPING = {
        "XBT": "BTC",
        "XXBT": "BTC",
        "XDG": "DOGE",
    }

    KRAKEN_QUOTE_MAPPING = {
        "ZEUR": "EUR",
        "ZUSD": "USD",
        "ZGBP": "GBP",
        "ZJPY": "JPY",
        "ZCAD": "CAD",
        "ZCHF": "CHF",
        "ZAUD": "AUD",
        "ZAED": "AED",
    }

    @classmethod
    def parse_pair(cls, pair_name: str) -> tuple[str, str]:
        pair_name = pair_name.upper().strip()

        for quote in cls.QUOTE_CURRENCIES:
            if pair_name.endswith(quote):
                base = pair_name[: -len(quote)]
                quote_currency = cls.KRAKEN_QUOTE_MAPPING.get(quote, quote)
                base_ticker = cls.KRAKEN_TICKER_MAPPING.get(base, base)
                return base_ticker, quote_currency

        raise ValueError(f"Cannot parse Kraken pair: {pair_name}")


class KrakenAssetCreator:
    # Fiat currencies
    FIAT_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CAD", "CHF", "AUD", "AED"}

    # Tier classification based on market cap/importance
    TIER1_ASSETS = {
        "BTC",
        "ETH",
        "USDT",
        "USDC",
        "BNB",
        "XRP",
        "ADA",
        "DOGE",
        "AVAX",
        "SOL",
        "MATIC",
        "DOT",
        "TRX",
        "DAI",
        "WBTC",
        "SHIB",
        "LTC",
        "LINK",
        "BCH",
        "ATOM",
    }

    TIER2_ASSETS = {
        "UNI",
        "XLM",
        "ETC",
        "ALGO",
        "AAVE",
        "FIL",
        "VET",
        "ICP",
        "NEAR",
        "APT",
        "GRT",
        "FTM",
        "SAND",
        "MANA",
        "AXS",
        "EGLD",
        "XTZ",
        "THETA",
        "CRO",
        "FLOW",
        "CHZ",
        "KSM",
        "CAKE",
        "ENS",
        "ZEC",
        "MKR",
        "COMP",
        "SNX",
        "SUSHI",
        "YFI",
    }

    TIER3_ASSETS = {
        "1INCH",
        "CRV",
        "BAT",
        "ENJ",
        "GALA",
        "LRC",
        "REN",
        "ZRX",
        "BAL",
        "KNC",
        "QTUM",
        "OMG",
        "ANKR",
        "STORJ",
        "BNT",
        "CELO",
        "OCEAN",
        "SKL",
        "NMR",
        "BAND",
        "ALPHA",
        "BADGER",
        "FARM",
        "PERP",
        "RUNE",
        "SRM",
        "TRB",
        "UMA",
        "XVS",
        "YFII",
    }

    def __init__(self, default_tier: str = None):
        self._asset_cache = {}
        self._default_tier = default_tier

    @classmethod
    def determine_category(cls, ticker: str) -> str:
        """Determine if an asset is a fiat currency or cryptocurrency."""
        ticker_upper = ticker.upper()
        if ticker_upper in cls.FIAT_CURRENCIES:
            return Asset.Category.CURRENCY
        return Asset.Category.CRYPTO

    @classmethod
    def determine_tier(cls, ticker: str) -> str:
        """Determine the appropriate tier for an asset based on its ticker."""
        ticker_upper = ticker.upper()

        if ticker_upper in cls.TIER1_ASSETS:
            return Asset.Tier.TIER1
        elif ticker_upper in cls.TIER2_ASSETS:
            return Asset.Tier.TIER2
        elif ticker_upper in cls.TIER3_ASSETS:
            return Asset.Tier.TIER3
        else:
            # Default to TIER4 for all other cryptos (small/speculative)
            return Asset.Tier.TIER4

    def get_or_create_asset(self, ticker: str, tier: str = None) -> Asset:
        cache_key = ticker

        if cache_key in self._asset_cache:
            return self._asset_cache[cache_key]

        # Determine tier: use provided tier, or default_tier, or auto-detect
        if tier is not None:
            asset_tier = tier
        elif self._default_tier is not None:
            asset_tier = self._default_tier
        else:
            # Auto-detect tier based on ticker
            asset_tier = self.determine_tier(ticker)

        # Determine category
        asset_category = self.determine_category(ticker)
        description = f"Cryptocurrency: {ticker}" if asset_category == Asset.Category.CRYPTO else f"Currency: {ticker}"

        asset, created = Asset.objects.get_or_create(
            ticker=ticker,
            defaults={
                "name": ticker,
                "category": asset_category,
                "tier": asset_tier,
                "description": description,
                "active": True,
            },
        )

        # Update tier if it was unclassified but now we have a specific tier
        if not created and asset.tier == Asset.Tier.UNCLASSIFIED and asset_tier != Asset.Tier.UNCLASSIFIED:
            asset.tier = asset_tier
            asset.save(update_fields=["tier"])

        self._asset_cache[cache_key] = asset
        return asset

    @transaction.atomic
    def bulk_create_assets(self, pair_names: list[str]) -> int:
        """Pre-create unique assets from trading pairs. Returns count of unique tickers."""
        unique_tickers = set()
        for pair_name in pair_names:
            try:
                base, _ = KrakenPairParser.parse_pair(pair_name)
                unique_tickers.add(base)
            except ValueError:
                continue

        existing_tickers = set(Asset.objects.filter(ticker__in=unique_tickers).values_list("ticker", flat=True))

        assets_to_create = []
        for ticker in unique_tickers:
            if ticker not in existing_tickers:
                # Use auto-tier determination for each asset
                asset_tier = self.determine_tier(ticker) if self._default_tier is None else self._default_tier
                # Determine category
                asset_category = self.determine_category(ticker)
                description = (
                    f"Cryptocurrency: {ticker}" if asset_category == Asset.Category.CRYPTO else f"Currency: {ticker}"
                )
                assets_to_create.append(
                    Asset(
                        ticker=ticker,
                        name=ticker,
                        category=asset_category,
                        tier=asset_tier,
                        description=description,
                        active=True,
                    )
                )

        if assets_to_create:
            Asset.objects.bulk_create(assets_to_create, ignore_conflicts=True)

        # Pre-populate cache for faster individual lookups
        all_assets = Asset.objects.filter(ticker__in=unique_tickers)
        for asset in all_assets:
            self._asset_cache[asset.ticker] = asset

        return len(unique_tickers)


def parse_ohlcv_csv(file_path: str, interval_minutes: int) -> Iterator[dict]:
    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) < 6:
                continue

            try:
                timestamp = datetime.fromtimestamp(int(row[0]), tz=dt_timezone.utc)
                yield {
                    "timestamp": timestamp,
                    "open": Decimal(row[1]),
                    "high": Decimal(row[2]),
                    "low": Decimal(row[3]),
                    "close": Decimal(row[4]),
                    "volume": Decimal(row[5]) if row[5] else None,
                    "trade_count": int(row[6]) if len(row) > 6 and row[6] else None,
                    "interval_minutes": interval_minutes,
                }
            except (ValueError, IndexError):
                continue
