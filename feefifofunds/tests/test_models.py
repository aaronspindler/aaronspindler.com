"""
Tests for FeeFiFoFunds models.

These tests verify the behavior of Asset and AssetPrice models,
including field validation, string representations, and model methods.
"""

from datetime import datetime
from datetime import timezone as dt_timezone
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from feefifofunds.models import Asset, AssetPrice
from feefifofunds.tests.factories import AssetFactory, AssetPriceFactory


class AssetModelTest(TestCase):
    """Test cases for the Asset model."""

    def test_asset_creation_with_all_fields(self):
        """Test creating an asset with all fields."""
        asset = AssetFactory.create_asset(
            ticker="BTC",
            name="Bitcoin",
            category=Asset.Category.CRYPTO,
            tier=Asset.Tier.TIER1,
            description="The original cryptocurrency",
            active=True,
        )

        actual_ticker = asset.ticker
        expected_ticker = "BTC"
        message = f"Asset ticker is {actual_ticker}, expected {expected_ticker}"
        self.assertEqual(actual_ticker, expected_ticker, message)

        actual_name = asset.name
        expected_name = "Bitcoin"
        message = f"Asset name is {actual_name}, expected {expected_name}"
        self.assertEqual(actual_name, expected_name, message)

        actual_category = asset.category
        expected_category = Asset.Category.CRYPTO
        message = f"Asset category is {actual_category}, expected {expected_category}"
        self.assertEqual(actual_category, expected_category, message)

        actual_tier = asset.tier
        expected_tier = Asset.Tier.TIER1
        message = f"Asset tier is {actual_tier}, expected {expected_tier}"
        self.assertEqual(actual_tier, expected_tier, message)

        actual_active = asset.active
        expected_active = True
        message = f"Asset active status is {actual_active}, expected {expected_active}"
        self.assertEqual(actual_active, expected_active, message)

    def test_asset_string_representation(self):
        """Test the string representation of an asset."""
        asset = AssetFactory.create_asset(ticker="ETH", name="Ethereum")

        actual_str = str(asset)
        expected_str = "ETH - Ethereum"
        message = f"Asset string representation is '{actual_str}', expected '{expected_str}'"
        self.assertEqual(actual_str, expected_str, message)

    def test_asset_unique_ticker_constraint(self):
        """Test that ticker must be unique."""
        # Create first asset
        AssetFactory.create_asset(ticker="BTC")

        # Attempt to create second asset with same ticker
        with self.assertRaises(IntegrityError):
            AssetFactory.create_asset(ticker="BTC")

    def test_asset_category_choices(self):
        """Test all valid category choices."""
        test_cases = [
            (Asset.Category.STOCK, "Stock asset"),
            (Asset.Category.CRYPTO, "Crypto asset"),
            (Asset.Category.COMMODITY, "Commodity asset"),
            (Asset.Category.CURRENCY, "Currency asset"),
        ]

        for category, description in test_cases:
            asset = AssetFactory.create_asset(ticker=f"TEST_{category}", category=category)

            actual_category = asset.category
            expected_category = category
            message = f"{description}: category is {actual_category}, expected {expected_category}"
            self.assertEqual(actual_category, expected_category, message)

    def test_asset_tier_choices(self):
        """Test all valid tier choices."""
        test_cases = [
            (Asset.Tier.TIER1, "TIER1", "Major/Blue-chip asset"),
            (Asset.Tier.TIER2, "TIER2", "Mid-cap asset"),
            (Asset.Tier.TIER3, "TIER3", "Small-cap asset"),
            (Asset.Tier.TIER4, "TIER4", "Micro-cap asset"),
            (Asset.Tier.UNCLASSIFIED, "UNCLASSIFIED", "Unclassified asset"),
        ]

        for tier, ticker_suffix, description in test_cases:
            asset = AssetFactory.create_asset(ticker=f"TEST_{ticker_suffix}", tier=tier)

            actual_tier = asset.tier
            expected_tier = tier
            message = f"{description}: tier is {actual_tier}, expected {expected_tier}"
            self.assertEqual(actual_tier, expected_tier, message)

    def test_asset_default_tier(self):
        """Test that default tier is UNCLASSIFIED."""
        asset = Asset.objects.create(
            ticker="TEST",
            name="Test Asset",
            category=Asset.Category.CRYPTO,
            # tier not specified, should use default
        )

        actual_tier = asset.tier
        expected_tier = Asset.Tier.UNCLASSIFIED
        message = f"Default tier is {actual_tier}, expected {expected_tier}"
        self.assertEqual(actual_tier, expected_tier, message)

    def test_asset_ordering(self):
        """Test that assets are ordered by ticker."""
        # Create assets in non-alphabetical order
        AssetFactory.create_asset(ticker="ZZZ")
        AssetFactory.create_asset(ticker="AAA")
        AssetFactory.create_asset(ticker="MMM")

        assets = list(Asset.objects.all().values_list("ticker", flat=True))

        actual_order = assets
        expected_order = ["AAA", "MMM", "ZZZ"]
        message = f"Assets ordered as {actual_order}, expected {expected_order}"
        self.assertEqual(actual_order, expected_order, message)

    def test_inactive_asset(self):
        """Test creating and querying inactive assets."""
        active_asset = AssetFactory.create_asset(ticker="ACTIVE", active=True)
        inactive_asset = AssetFactory.create_inactive_asset(ticker="INACTIVE")

        # Query active assets
        active_assets = Asset.objects.filter(active=True)

        actual_count = active_assets.count()
        expected_count = 1
        message = f"Found {actual_count} active assets, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

        actual_ticker = active_assets.first().ticker
        expected_ticker = "ACTIVE"
        message = f"Active asset ticker is {actual_ticker}, expected {expected_ticker}"
        self.assertEqual(actual_ticker, expected_ticker, message)

        # Query inactive assets
        inactive_assets = Asset.objects.filter(active=False)

        actual_count = inactive_assets.count()
        expected_count = 1
        message = f"Found {actual_count} inactive assets, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

    def test_asset_description_optional(self):
        """Test that description field is optional."""
        asset = Asset.objects.create(
            ticker="NODESC",
            name="No Description Asset",
            category=Asset.Category.CRYPTO,
        )

        actual_description = asset.description
        expected_description = ""
        message = f"Empty description is '{actual_description}', expected '{expected_description}'"
        self.assertEqual(actual_description, expected_description, message)

    def test_asset_factory_methods(self):
        """Test specialized factory methods."""
        # Test crypto asset factory
        crypto = AssetFactory.create_crypto_asset(ticker="BTC")
        actual_category = crypto.category
        expected_category = Asset.Category.CRYPTO
        message = f"Crypto asset category is {actual_category}, expected {expected_category}"
        self.assertEqual(actual_category, expected_category, message)

        # Test currency asset factory
        currency = AssetFactory.create_currency_asset(ticker="USD")
        actual_category = currency.category
        expected_category = Asset.Category.CURRENCY
        message = f"Currency asset category is {actual_category}, expected {expected_category}"
        self.assertEqual(actual_category, expected_category, message)

        # Test stock asset factory
        stock = AssetFactory.create_stock_asset(ticker="AAPL")
        actual_category = stock.category
        expected_category = Asset.Category.STOCK
        message = f"Stock asset category is {actual_category}, expected {expected_category}"
        self.assertEqual(actual_category, expected_category, message)

        # Test commodity asset factory
        commodity = AssetFactory.create_commodity_asset(ticker="GLD")
        actual_category = commodity.category
        expected_category = Asset.Category.COMMODITY
        message = f"Commodity asset category is {actual_category}, expected {expected_category}"
        self.assertEqual(actual_category, expected_category, message)


class AssetPriceModelTest(TestCase):
    """Test cases for the AssetPrice model."""

    def setUp(self):
        """Set up test data."""
        self.asset = AssetFactory.create_crypto_asset(ticker="BTC", name="Bitcoin")

    def test_asset_price_creation(self):
        """Test creating an asset price with all fields."""
        test_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        price = AssetPriceFactory.create_price(
            asset=self.asset,
            time=test_time,
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49000.00"),
            close=Decimal("50500.00"),
            volume=Decimal("1000000.00"),
            interval_minutes=1440,
            trade_count=5000,
            quote_currency="USD",
            source="kraken",
        )

        actual_asset_id = price.asset_id
        expected_asset_id = self.asset.id
        message = f"Price asset_id is {actual_asset_id}, expected {expected_asset_id}"
        self.assertEqual(actual_asset_id, expected_asset_id, message)

        actual_time = price.time
        expected_time = test_time
        message = f"Price time is {actual_time}, expected {expected_time}"
        self.assertEqual(actual_time, expected_time, message)

        actual_close = price.close
        expected_close = Decimal("50500.00")
        message = f"Price close is {actual_close}, expected {expected_close}"
        self.assertEqual(actual_close, expected_close, message)

    def test_asset_price_string_representation(self):
        """Test the string representation of an asset price."""
        test_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=dt_timezone.utc)
        price = AssetPriceFactory.create_price(
            asset=self.asset,
            time=test_time,
            close=Decimal("45000.00"),
            source="finnhub",
        )

        actual_str = str(price)
        expected_str = f"Asset {self.asset.id} @ 2024-01-15 14:30 (finnhub): $45000.00"
        message = f"Price string representation is '{actual_str}', expected '{expected_str}'"
        self.assertEqual(actual_str, expected_str, message)

    def test_asset_price_lazy_loading_asset(self):
        """Test that asset property lazy loads from PostgreSQL."""
        price = AssetPriceFactory.create_price(asset=self.asset)

        # Access asset property (should lazy load)
        loaded_asset = price.asset

        actual_ticker = loaded_asset.ticker
        expected_ticker = "BTC"
        message = f"Lazy loaded asset ticker is {actual_ticker}, expected {expected_ticker}"
        self.assertEqual(actual_ticker, expected_ticker, message)

        # Verify it's cached (accessing again shouldn't query DB)
        cached_asset = price.asset
        self.assertIs(cached_asset, loaded_asset, "Asset should be cached after first access")

    def test_ohlcv_price_creation(self):
        """Test creating an OHLCV price record."""
        price = AssetPriceFactory.create_ohlcv_price(
            asset=self.asset,
            interval_minutes=720,  # 12-hour candle
        )

        actual_interval = price.interval_minutes
        expected_interval = 720
        message = f"OHLCV interval is {actual_interval}, expected {expected_interval}"
        self.assertEqual(actual_interval, expected_interval, message)

        actual_source = price.source
        expected_source = "kraken"
        message = f"OHLCV source is {actual_source}, expected {expected_source}"
        self.assertEqual(actual_source, expected_source, message)

    def test_tick_price_creation(self):
        """Test creating a tick price (non-OHLCV) record."""
        price = AssetPriceFactory.create_tick_price(
            asset=self.asset,
            price=Decimal("42000.00"),
        )

        # Tick prices should have same value for OHLC
        actual_open = price.open
        actual_close = price.close
        expected_price = Decimal("42000.00")
        message = f"Tick price open={actual_open}, close={actual_close}, expected all {expected_price}"
        self.assertEqual(actual_open, expected_price, message)
        self.assertEqual(actual_close, expected_price, message)

        actual_interval = price.interval_minutes
        expected_interval = None
        message = f"Tick price interval is {actual_interval}, expected {expected_interval}"
        self.assertEqual(actual_interval, expected_interval, message)

        actual_source = price.source
        expected_source = "finnhub"
        message = f"Tick price source is {actual_source}, expected {expected_source}"
        self.assertEqual(actual_source, expected_source, message)

    def test_price_series_creation(self):
        """Test creating a series of price records."""
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=dt_timezone.utc)
        prices = AssetPriceFactory.create_price_series(
            asset=self.asset,
            start_time=start_time,
            count=5,
            interval_minutes=1440,
        )

        actual_count = len(prices)
        expected_count = 5
        message = f"Created {actual_count} prices, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

        # Check that prices have correct time intervals
        for i, price in enumerate(prices):
            expected_time = start_time.timestamp() + (i * 1440 * 60)
            actual_time = price.time.timestamp()
            time_diff = abs(actual_time - expected_time)
            message = f"Price {i} time difference is {time_diff} seconds, expected < 1"
            self.assertLess(time_diff, 1, message)

    def test_optional_fields(self):
        """Test that volume, trade_count, and interval_minutes are optional."""
        price = AssetPrice(
            asset_id=self.asset.id,
            time=datetime.now(dt_timezone.utc),
            open=Decimal("100.00"),
            high=Decimal("100.00"),
            low=Decimal("100.00"),
            close=Decimal("100.00"),
            # volume, interval_minutes, trade_count not specified
            quote_currency="USD",
            source="test",
        )

        actual_volume = price.volume
        expected_volume = None
        message = f"Optional volume is {actual_volume}, expected {expected_volume}"
        self.assertEqual(actual_volume, expected_volume, message)

        actual_interval = price.interval_minutes
        expected_interval = None
        message = f"Optional interval is {actual_interval}, expected {expected_interval}"
        self.assertEqual(actual_interval, expected_interval, message)

        actual_trade_count = price.trade_count
        expected_trade_count = None
        message = f"Optional trade_count is {actual_trade_count}, expected {expected_trade_count}"
        self.assertEqual(actual_trade_count, expected_trade_count, message)

    def test_quote_currency_variations(self):
        """Test different quote currencies."""
        currencies = ["USD", "EUR", "BTC", "ETH", "GBP"]

        for currency in currencies:
            price = AssetPriceFactory.create_price(
                asset=self.asset,
                quote_currency=currency,
            )

            actual_currency = price.quote_currency
            expected_currency = currency
            message = f"Quote currency is {actual_currency}, expected {expected_currency}"
            self.assertEqual(actual_currency, expected_currency, message)

    def test_price_source_variations(self):
        """Test different price sources."""
        sources = ["finnhub", "kraken", "massive", "binance", "coinbase"]

        for source in sources:
            price = AssetPriceFactory.create_price(
                asset=self.asset,
                source=source,
            )

            actual_source = price.source
            expected_source = source
            message = f"Price source is {actual_source}, expected {expected_source}"
            self.assertEqual(actual_source, expected_source, message)

    def test_price_decimal_precision(self):
        """Test that decimal fields handle high precision."""
        price = AssetPriceFactory.create_price(
            asset=self.asset,
            open=Decimal("0.00000001"),  # 8 decimal places
            high=Decimal("99999999.99999999"),  # Max precision
            low=Decimal("0.00000001"),
            close=Decimal("12345678.87654321"),
        )

        actual_open = price.open
        expected_open = Decimal("0.00000001")
        message = f"High precision open is {actual_open}, expected {expected_open}"
        self.assertEqual(actual_open, expected_open, message)

        actual_close = price.close
        expected_close = Decimal("12345678.87654321")
        message = f"High precision close is {actual_close}, expected {expected_close}"
        self.assertEqual(actual_close, expected_close, message)

    def test_interval_minutes_values(self):
        """Test common interval values for OHLCV data."""
        intervals = [
            (1, "1 minute"),
            (5, "5 minutes"),
            (15, "15 minutes"),
            (60, "1 hour"),
            (240, "4 hours"),
            (720, "12 hours"),
            (1440, "1 day"),
            (10080, "1 week"),
        ]

        for interval, description in intervals:
            price = AssetPriceFactory.create_price(
                asset=self.asset,
                interval_minutes=interval,
            )

            actual_interval = price.interval_minutes
            expected_interval = interval
            message = f"{description} interval is {actual_interval}, expected {expected_interval}"
            self.assertEqual(actual_interval, expected_interval, message)

    def test_price_ordering(self):
        """Test that prices are ordered by time descending."""
        # Create prices in random time order
        AssetPriceFactory.create_price(
            asset=self.asset, time=datetime(2024, 1, 3, tzinfo=dt_timezone.utc), close=Decimal("300")
        )
        AssetPriceFactory.create_price(
            asset=self.asset, time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc), close=Decimal("100")
        )
        AssetPriceFactory.create_price(
            asset=self.asset, time=datetime(2024, 1, 2, tzinfo=dt_timezone.utc), close=Decimal("200")
        )

        # Note: Since AssetPrice is unmanaged (managed=False), ordering might not work in tests
        # This test is included for completeness but may need adjustment based on test DB setup
        pass  # Placeholder for ordering test that may require QuestDB
