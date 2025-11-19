"""
Test data factories for creating consistent fake FeeFiFoFunds data across all tests.

This module provides factory functions to create test Asset and AssetPrice instances
with consistent, realistic fake data that can be reused across all test files.
"""

from datetime import datetime
from datetime import timezone as dt_timezone
from decimal import Decimal


class AssetFactory:
    """Factory for creating test assets."""

    @staticmethod
    def create_asset(
        ticker="BTC",
        name=None,
        category="CRYPTO",
        tier="TIER1",
        description=None,
        active=True,
        **kwargs,
    ):
        """Create an asset with default test data."""
        from feefifofunds.models import Asset

        # Auto-generate name if not provided
        if name is None:
            name = f"{ticker} Asset"

        # Auto-generate description if not provided
        if description is None:
            if category == Asset.Category.CRYPTO:
                description = f"Cryptocurrency: {ticker}"
            elif category == Asset.Category.CURRENCY:
                description = f"Currency: {ticker}"
            elif category == Asset.Category.STOCK:
                description = f"Stock: {ticker}"
            else:
                description = f"{category}: {ticker}"

        return Asset.objects.create(
            ticker=ticker,
            name=name,
            category=category,
            tier=tier,
            description=description,
            active=active,
            **kwargs,
        )

    @staticmethod
    def create_crypto_asset(ticker="BTC", name="Bitcoin", tier="TIER1", **kwargs):
        """Create a cryptocurrency asset."""
        return AssetFactory.create_asset(
            ticker=ticker,
            name=name,
            category="CRYPTO",
            tier=tier,
            **kwargs,
        )

    @staticmethod
    def create_currency_asset(ticker="USD", name="US Dollar", **kwargs):
        """Create a fiat currency asset."""
        return AssetFactory.create_asset(
            ticker=ticker,
            name=name,
            category="CURRENCY",
            tier="TIER1",  # Currencies are typically TIER1
            **kwargs,
        )

    @staticmethod
    def create_stock_asset(ticker="AAPL", name="Apple Inc.", tier="TIER1", **kwargs):
        """Create a stock/ETF asset."""
        return AssetFactory.create_asset(
            ticker=ticker,
            name=name,
            category="STOCK",
            tier=tier,
            **kwargs,
        )

    @staticmethod
    def create_commodity_asset(ticker="GLD", name="Gold", tier="TIER1", **kwargs):
        """Create a commodity asset."""
        return AssetFactory.create_asset(
            ticker=ticker,
            name=name,
            category="COMMODITY",
            tier=tier,
            **kwargs,
        )

    @staticmethod
    def create_inactive_asset(**kwargs):
        """Create an inactive asset."""
        kwargs.setdefault("active", False)
        return AssetFactory.create_asset(**kwargs)


class AssetPriceFactory:
    """Factory for creating test asset prices."""

    @staticmethod
    def create_price(
        asset=None,
        asset_id=None,
        time=None,
        open=Decimal("100.00"),
        high=Decimal("105.00"),
        low=Decimal("95.00"),
        close=Decimal("102.50"),
        volume=Decimal("1000000.00"),
        interval_minutes=1440,
        trade_count=1500,
        quote_currency="USD",
        source="test",
        **kwargs,
    ):
        """Create an asset price with default test data."""
        from feefifofunds.models import AssetPrice

        # Handle asset/asset_id
        if asset_id is None and asset is not None:
            asset_id = asset.id
        elif asset_id is None:
            # Create a default asset if none provided
            asset = AssetFactory.create_crypto_asset()
            asset_id = asset.id

        # Use current time if not provided
        if time is None:
            time = datetime.now(dt_timezone.utc)

        # Create the price - Note: AssetPrice uses QuestDB, may need special handling in tests
        return AssetPrice(
            asset_id=asset_id,
            time=time,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            interval_minutes=interval_minutes,
            trade_count=trade_count,
            quote_currency=quote_currency,
            source=source,
            **kwargs,
        )

    @staticmethod
    def create_ohlcv_price(
        asset=None,
        time=None,
        interval_minutes=1440,
        **kwargs,
    ):
        """Create an OHLCV (candlestick) price record."""
        return AssetPriceFactory.create_price(
            asset=asset,
            time=time,
            interval_minutes=interval_minutes,
            source="kraken",
            **kwargs,
        )

    @staticmethod
    def create_tick_price(
        asset=None,
        time=None,
        price=Decimal("100.00"),
        **kwargs,
    ):
        """Create a tick price (no OHLCV, just close price)."""
        return AssetPriceFactory.create_price(
            asset=asset,
            time=time,
            open=price,
            high=price,
            low=price,
            close=price,
            interval_minutes=None,  # No interval for tick data
            trade_count=None,
            volume=None,
            source="finnhub",
            **kwargs,
        )

    @staticmethod
    def create_price_series(
        asset=None,
        start_time=None,
        count=10,
        interval_minutes=1440,
        base_price=Decimal("100.00"),
        volatility=Decimal("0.05"),
    ):
        """Create a series of price records with realistic variations."""
        import random
        from datetime import timedelta

        if start_time is None:
            start_time = datetime.now(dt_timezone.utc) - timedelta(days=count)

        prices = []
        current_price = base_price

        for i in range(count):
            # Add some realistic price variation
            change_factor = Decimal(1 + random.uniform(-float(volatility), float(volatility)))
            new_price = current_price * change_factor

            # Calculate OHLC with some variation
            daily_volatility = new_price * Decimal("0.02")
            high = new_price + daily_volatility * Decimal(random.uniform(0, 1))
            low = new_price - daily_volatility * Decimal(random.uniform(0, 1))
            open_price = new_price + daily_volatility * Decimal(random.uniform(-0.5, 0.5))
            close_price = new_price + daily_volatility * Decimal(random.uniform(-0.5, 0.5))

            price_time = start_time + timedelta(minutes=interval_minutes * i)

            prices.append(
                AssetPriceFactory.create_price(
                    asset=asset,
                    time=price_time,
                    open=open_price.quantize(Decimal("0.00000001")),
                    high=high.quantize(Decimal("0.00000001")),
                    low=low.quantize(Decimal("0.00000001")),
                    close=close_price.quantize(Decimal("0.00000001")),
                    volume=Decimal(random.randint(100000, 10000000)),
                    interval_minutes=interval_minutes,
                    trade_count=random.randint(100, 5000),
                )
            )

            current_price = new_price

        return prices


class MockDataFactory:
    """Factory for creating mock FeeFiFoFunds data."""

    @staticmethod
    def get_common_tickers():
        """Get commonly used tickers for testing."""
        return {
            "crypto": ["BTC", "ETH", "USDT", "USDC", "BNB", "XRP", "ADA", "DOGE"],
            "currency": ["USD", "EUR", "GBP", "JPY", "CAD", "CHF", "AUD"],
            "stock": ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META"],
            "commodity": ["GLD", "SLV", "OIL", "NATGAS"],
        }

    @staticmethod
    def get_kraken_pairs():
        """Get common Kraken trading pairs for testing."""
        return [
            "XBTUSD",  # BTC/USD
            "XBTEUR",  # BTC/EUR
            "XBTCAD",  # BTC/CAD
            "ETHUSD",  # ETH/USD
            "XXBTZUSD",  # Alternative BTC/USD format
            "XXBTZCAD",  # Alternative BTC/CAD format
            "ADAUSD",  # ADA/USD
            "DOGEUSD",  # DOGE/USD
        ]

    @staticmethod
    def get_tier_classifications():
        """Get tier classification examples for testing."""
        return {
            "TIER1": ["BTC", "ETH", "USDT", "USDC", "USD", "EUR"],
            "TIER2": ["UNI", "ALGO", "AAVE", "FIL"],
            "TIER3": ["1INCH", "CRV", "BAT", "ENJ"],
            "TIER4": ["UNKNOWN", "RANDOM", "TESTCOIN"],
            "UNCLASSIFIED": ["NEW", "UNLISTED"],
        }

    @staticmethod
    def get_test_csv_row(
        timestamp=1609459200,  # 2021-01-01 00:00:00 UTC
        open="29000.00",
        high="29500.00",
        low="28500.00",
        close="29250.00",
        volume="1234567.89",
        trade_count="1500",
    ):
        """Get a sample CSV row for OHLCV data testing."""
        return {
            "timestamp": timestamp,
            "open": open,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "trade_count": trade_count,
        }
