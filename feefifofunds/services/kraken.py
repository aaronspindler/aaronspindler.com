import csv
from datetime import datetime
from datetime import timezone as dt_timezone
from decimal import Decimal
from typing import Iterator

from django.db import transaction

from feefifofunds.models import Asset


class KrakenPairParser:
    QUOTE_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "CHF", "AUD", "AED", "XBT", "ETH", "DAI", "DOT", "POL"]

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
    def __init__(self):
        self._asset_cache = {}

    def get_or_create_asset(self, ticker: str, quote_currency: str) -> Asset:
        cache_key = (ticker, quote_currency)

        if cache_key in self._asset_cache:
            return self._asset_cache[cache_key]

        asset, created = Asset.objects.get_or_create(
            ticker=ticker,
            defaults={
                "name": ticker,
                "category": Asset.Category.CRYPTO,
                "quote_currency": quote_currency,
                "description": f"Kraken trading pair: {ticker}/{quote_currency}",
                "active": True,
            },
        )

        self._asset_cache[cache_key] = asset
        return asset

    @transaction.atomic
    def bulk_create_assets(self, pair_names: list[str]) -> dict[str, Asset]:
        parsed_pairs = {}
        for pair_name in pair_names:
            try:
                base, quote = KrakenPairParser.parse_pair(pair_name)
                parsed_pairs[pair_name] = (base, quote)
            except ValueError:
                continue

        existing_tickers = set(
            Asset.objects.filter(ticker__in=[p[0] for p in parsed_pairs.values()]).values_list("ticker", flat=True)
        )

        assets_to_create = []
        for pair_name, (base, quote) in parsed_pairs.items():
            if base not in existing_tickers:
                assets_to_create.append(
                    Asset(
                        ticker=base,
                        name=base,
                        category=Asset.Category.CRYPTO,
                        quote_currency=quote,
                        description=f"Kraken trading pair: {base}/{quote}",
                        active=True,
                    )
                )
                existing_tickers.add(base)

        if assets_to_create:
            Asset.objects.bulk_create(assets_to_create, ignore_conflicts=True)

        all_assets = Asset.objects.filter(ticker__in=[p[0] for p in parsed_pairs.values()])
        asset_map = {asset.ticker: asset for asset in all_assets}

        result = {}
        for pair_name, (base, quote) in parsed_pairs.items():
            if base in asset_map:
                result[pair_name] = asset_map[base]
                self._asset_cache[(base, quote)] = asset_map[base]

        return result


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


def parse_trade_csv(file_path: str) -> Iterator[dict]:
    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) < 3:
                continue

            try:
                timestamp = datetime.fromtimestamp(int(row[0]), tz=dt_timezone.utc)
                yield {
                    "timestamp": timestamp,
                    "price": Decimal(row[1]),
                    "volume": Decimal(row[2]),
                }
            except (ValueError, IndexError):
                continue


class BulkInsertHelper:
    @staticmethod
    def bulk_create_prices(prices: list, batch_size: int = 25000):
        from feefifofunds.models import AssetPrice

        for i in range(0, len(prices), batch_size):
            batch = prices[i : i + batch_size]
            AssetPrice.objects.bulk_create(batch, ignore_conflicts=True)

    @staticmethod
    def bulk_create_trades(trades: list, batch_size: int = 50000):
        from feefifofunds.models import Trade

        for i in range(0, len(trades), batch_size):
            batch = trades[i : i + batch_size]
            Trade.objects.bulk_create(batch, ignore_conflicts=True)
