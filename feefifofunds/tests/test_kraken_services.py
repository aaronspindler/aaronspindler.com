"""
Tests for Kraken service classes.

These tests verify the functionality of KrakenPairParser and KrakenAssetCreator,
including pair parsing, ticker mapping, tier determination, and asset creation.
"""

import csv
import tempfile
from datetime import datetime
from datetime import timezone as dt_timezone
from decimal import Decimal
from pathlib import Path

from django.test import TestCase

from feefifofunds.models import Asset
from feefifofunds.services.kraken import (
    KrakenAssetCreator,
    KrakenPairParser,
    parse_ohlcv_csv,
)
from feefifofunds.tests.factories import AssetFactory


class KrakenPairParserTest(TestCase):
    """Test cases for the KrakenPairParser class."""

    def test_parse_standard_pairs(self):
        """Test parsing standard Kraken trading pairs."""
        test_cases = [
            ("XBTUSD", "BTC", "USD", "Standard BTC/USD pair"),
            ("XBTEUR", "BTC", "EUR", "Standard BTC/EUR pair"),
            ("XBTCAD", "BTC", "CAD", "Standard BTC/CAD pair"),
            ("XBTGBP", "BTC", "GBP", "Standard BTC/GBP pair"),
            ("ETHUSD", "ETH", "USD", "ETH/USD pair"),
            ("ADAUSD", "ADA", "USD", "ADA/USD pair"),
            ("DOGEUSD", "DOGE", "USD", "DOGE/USD pair"),
        ]

        for pair_name, expected_base, expected_quote, description in test_cases:
            actual_base, actual_quote = KrakenPairParser.parse_pair(pair_name)

            base_message = f"{description}: base is {actual_base}, expected {expected_base}"
            self.assertEqual(actual_base, expected_base, base_message)

            quote_message = f"{description}: quote is {actual_quote}, expected {expected_quote}"
            self.assertEqual(actual_quote, expected_quote, quote_message)

    def test_parse_z_prefixed_pairs(self):
        """Test parsing Kraken pairs with Z-prefixed quote currencies."""
        test_cases = [
            ("XXBTZUSD", "BTC", "USD", "BTC with Z-prefixed USD"),
            ("XXBTZEUR", "BTC", "EUR", "BTC with Z-prefixed EUR"),
            ("XXBTZCAD", "BTC", "CAD", "BTC with Z-prefixed CAD"),
            ("ETHZUSD", "ETH", "USD", "ETH with Z-prefixed USD"),
            ("ADAZEUR", "ADA", "EUR", "ADA with Z-prefixed EUR"),
        ]

        for pair_name, expected_base, expected_quote, description in test_cases:
            actual_base, actual_quote = KrakenPairParser.parse_pair(pair_name)

            base_message = f"{description}: base is {actual_base}, expected {expected_base}"
            self.assertEqual(actual_base, expected_base, base_message)

            quote_message = f"{description}: quote is {actual_quote}, expected {expected_quote}"
            self.assertEqual(actual_quote, expected_quote, quote_message)

    def test_parse_alternative_ticker_formats(self):
        """Test parsing pairs with alternative ticker formats."""
        test_cases = [
            ("XXBTUSD", "BTC", "USD", "XXBT format for BTC"),
            ("XXBTEUR", "BTC", "EUR", "XXBT format with EUR"),
            ("XDGUSD", "DOGE", "USD", "XDG format for DOGE"),
            ("XDGEUR", "DOGE", "EUR", "XDG format with EUR"),
        ]

        for pair_name, expected_base, expected_quote, description in test_cases:
            actual_base, actual_quote = KrakenPairParser.parse_pair(pair_name)

            base_message = f"{description}: base is {actual_base}, expected {expected_base}"
            self.assertEqual(actual_base, expected_base, base_message)

            quote_message = f"{description}: quote is {actual_quote}, expected {expected_quote}"
            self.assertEqual(actual_quote, expected_quote, quote_message)

    def test_parse_crypto_quote_pairs(self):
        """Test parsing pairs with cryptocurrency as quote currency."""
        test_cases = [
            ("ADAXBT", "ADA", "XBT", "ADA priced in Bitcoin"),
            ("ETHXBT", "ETH", "XBT", "ETH priced in Bitcoin"),
            ("ADAETH", "ADA", "ETH", "ADA priced in Ethereum"),
            ("DOTETH", "DOT", "ETH", "Polkadot priced in Ethereum"),
            ("USDTDAI", "USDT", "DAI", "USDT priced in DAI"),
        ]

        for pair_name, expected_base, expected_quote, description in test_cases:
            actual_base, actual_quote = KrakenPairParser.parse_pair(pair_name)

            base_message = f"{description}: base is {actual_base}, expected {expected_base}"
            self.assertEqual(actual_base, expected_base, base_message)

            quote_message = f"{description}: quote is {actual_quote}, expected {expected_quote}"
            self.assertEqual(actual_quote, expected_quote, quote_message)

    def test_parse_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        test_cases = [
            ("xbtusd", "BTC", "USD", "Lowercase input"),
            ("XBTUSD", "BTC", "USD", "Uppercase input"),
            ("XbTuSd", "BTC", "USD", "Mixed case input"),
        ]

        for pair_name, expected_base, expected_quote, description in test_cases:
            actual_base, actual_quote = KrakenPairParser.parse_pair(pair_name)

            base_message = f"{description}: base is {actual_base}, expected {expected_base}"
            self.assertEqual(actual_base, expected_base, base_message)

            quote_message = f"{description}: quote is {actual_quote}, expected {expected_quote}"
            self.assertEqual(actual_quote, expected_quote, quote_message)

    def test_parse_with_whitespace(self):
        """Test that parsing handles whitespace."""
        test_cases = [
            ("  XBTUSD", "BTC", "USD", "Leading whitespace"),
            ("XBTUSD  ", "BTC", "USD", "Trailing whitespace"),
            ("  XBTUSD  ", "BTC", "USD", "Both whitespace"),
        ]

        for pair_name, expected_base, expected_quote, description in test_cases:
            actual_base, actual_quote = KrakenPairParser.parse_pair(pair_name)

            base_message = f"{description}: base is {actual_base}, expected {expected_base}"
            self.assertEqual(actual_base, expected_base, base_message)

            quote_message = f"{description}: quote is {actual_quote}, expected {expected_quote}"
            self.assertEqual(actual_quote, expected_quote, quote_message)

    def test_parse_invalid_pair_raises_error(self):
        """Test that invalid pairs raise ValueError."""
        invalid_pairs = [
            "INVALID",  # No recognized quote currency
            "XBT",  # Just a ticker, no pair
            "123456",  # Numbers only
            "",  # Empty string
            "BTCXYZ",  # Invalid quote currency
        ]

        for invalid_pair in invalid_pairs:
            with self.assertRaises(ValueError) as context:
                KrakenPairParser.parse_pair(invalid_pair)

            actual_message = str(context.exception)
            expected_fragment = f"Cannot parse Kraken pair: {invalid_pair.upper().strip()}"
            message = f"Error message '{actual_message}' should contain '{expected_fragment}'"
            self.assertIn(expected_fragment, actual_message, message)

    def test_longest_match_wins(self):
        """Test that longer quote currency matches are preferred."""
        # This tests that ZUSD is matched before USD
        pair_name = "BTCZUSD"  # Should match ZUSD, not USD
        actual_base, actual_quote = KrakenPairParser.parse_pair(pair_name)

        expected_base = "BTC"
        expected_quote = "USD"  # ZUSD maps to USD
        base_message = f"Base is {actual_base}, expected {expected_base}"
        self.assertEqual(actual_base, expected_base, base_message)

        quote_message = f"Quote is {actual_quote}, expected {expected_quote}"
        self.assertEqual(actual_quote, expected_quote, quote_message)


class KrakenAssetCreatorTest(TestCase):
    """Test cases for the KrakenAssetCreator class."""

    def setUp(self):
        """Set up test data."""
        self.creator = KrakenAssetCreator()

    def test_determine_tier_for_tier1_assets(self):
        """Test tier determination for TIER1 assets."""
        tier1_assets = ["BTC", "ETH", "USDT", "USDC", "BNB", "XRP", "ADA", "DOGE", "SOL", "MATIC"]

        for ticker in tier1_assets:
            actual_tier = KrakenAssetCreator.determine_tier(ticker)
            expected_tier = Asset.Tier.TIER1
            message = f"{ticker} tier is {actual_tier}, expected {expected_tier}"
            self.assertEqual(actual_tier, expected_tier, message)

    def test_determine_tier_for_tier2_assets(self):
        """Test tier determination for TIER2 assets."""
        tier2_assets = ["UNI", "ALGO", "AAVE", "FIL", "GRT", "SAND", "MKR", "COMP", "YFI"]

        for ticker in tier2_assets:
            actual_tier = KrakenAssetCreator.determine_tier(ticker)
            expected_tier = Asset.Tier.TIER2
            message = f"{ticker} tier is {actual_tier}, expected {expected_tier}"
            self.assertEqual(actual_tier, expected_tier, message)

    def test_determine_tier_for_tier3_assets(self):
        """Test tier determination for TIER3 assets."""
        tier3_assets = ["1INCH", "CRV", "BAT", "ENJ", "GALA", "LRC", "REN", "OCEAN", "RUNE"]

        for ticker in tier3_assets:
            actual_tier = KrakenAssetCreator.determine_tier(ticker)
            expected_tier = Asset.Tier.TIER3
            message = f"{ticker} tier is {actual_tier}, expected {expected_tier}"
            self.assertEqual(actual_tier, expected_tier, message)

    def test_determine_tier_for_unknown_assets(self):
        """Test that unknown assets default to TIER4."""
        unknown_assets = ["UNKNOWN", "RANDOM", "TESTCOIN", "XYZ", "ABC123"]

        for ticker in unknown_assets:
            actual_tier = KrakenAssetCreator.determine_tier(ticker)
            expected_tier = Asset.Tier.TIER4
            message = f"{ticker} tier is {actual_tier}, expected {expected_tier}"
            self.assertEqual(actual_tier, expected_tier, message)

    def test_determine_tier_case_insensitive(self):
        """Test that tier determination is case-insensitive."""
        test_cases = [
            ("btc", Asset.Tier.TIER1, "Lowercase BTC"),
            ("BTC", Asset.Tier.TIER1, "Uppercase BTC"),
            ("Btc", Asset.Tier.TIER1, "Mixed case BTC"),
            ("uni", Asset.Tier.TIER2, "Lowercase UNI"),
            ("1inch", Asset.Tier.TIER3, "Lowercase 1INCH"),
        ]

        for ticker, expected_tier, description in test_cases:
            actual_tier = KrakenAssetCreator.determine_tier(ticker)
            message = f"{description}: tier is {actual_tier}, expected {expected_tier}"
            self.assertEqual(actual_tier, expected_tier, message)

    def test_determine_category_for_fiat(self):
        """Test category determination for fiat currencies."""
        fiat_currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "CHF", "AUD", "AED"]

        for ticker in fiat_currencies:
            actual_category = KrakenAssetCreator.determine_category(ticker)
            expected_category = Asset.Category.CURRENCY
            message = f"{ticker} category is {actual_category}, expected {expected_category}"
            self.assertEqual(actual_category, expected_category, message)

    def test_determine_category_for_crypto(self):
        """Test category determination for cryptocurrencies."""
        crypto_assets = ["BTC", "ETH", "ADA", "DOGE", "UNI", "UNKNOWN"]

        for ticker in crypto_assets:
            actual_category = KrakenAssetCreator.determine_category(ticker)
            expected_category = Asset.Category.CRYPTO
            message = f"{ticker} category is {actual_category}, expected {expected_category}"
            self.assertEqual(actual_category, expected_category, message)

    def test_get_or_create_asset_creates_new(self):
        """Test that get_or_create_asset creates new assets."""
        asset = self.creator.get_or_create_asset("BTC")

        actual_ticker = asset.ticker
        expected_ticker = "BTC"
        message = f"Asset ticker is {actual_ticker}, expected {expected_ticker}"
        self.assertEqual(actual_ticker, expected_ticker, message)

        actual_category = asset.category
        expected_category = Asset.Category.CRYPTO
        message = f"Asset category is {actual_category}, expected {expected_category}"
        self.assertEqual(actual_category, expected_category, message)

        actual_tier = asset.tier
        expected_tier = Asset.Tier.TIER1
        message = f"Asset tier is {actual_tier}, expected {expected_tier}"
        self.assertEqual(actual_tier, expected_tier, message)

    def test_get_or_create_asset_returns_existing(self):
        """Test that get_or_create_asset returns existing assets."""
        # Create an asset first
        original = AssetFactory.create_crypto_asset(ticker="ETH", name="Original Ethereum")

        # Try to get_or_create the same ticker
        asset = self.creator.get_or_create_asset("ETH")

        actual_id = asset.id
        expected_id = original.id
        message = f"Returned asset ID is {actual_id}, expected {expected_id} (should be existing)"
        self.assertEqual(actual_id, expected_id, message)

        actual_name = asset.name
        expected_name = "Original Ethereum"
        message = f"Asset name is '{actual_name}', expected '{expected_name}' (unchanged)"
        self.assertEqual(actual_name, expected_name, message)

    def test_get_or_create_asset_with_cache(self):
        """Test that asset cache prevents duplicate DB queries."""
        # First call should create and cache
        asset1 = self.creator.get_or_create_asset("SOL")

        # Second call should return from cache
        asset2 = self.creator.get_or_create_asset("SOL")

        # Should be the exact same object (not just equal)
        self.assertIs(asset1, asset2, "Second call should return cached asset object")

    def test_get_or_create_asset_with_explicit_tier(self):
        """Test providing explicit tier overrides auto-detection."""
        asset = self.creator.get_or_create_asset("BTC", tier=Asset.Tier.TIER3)

        actual_tier = asset.tier
        expected_tier = Asset.Tier.TIER3
        message = f"Explicit tier is {actual_tier}, expected {expected_tier}"
        self.assertEqual(actual_tier, expected_tier, message)

    def test_get_or_create_asset_with_default_tier(self):
        """Test that default_tier is used when set."""
        creator_with_default = KrakenAssetCreator(default_tier=Asset.Tier.TIER2)
        asset = creator_with_default.get_or_create_asset("UNKNOWN")

        actual_tier = asset.tier
        expected_tier = Asset.Tier.TIER2
        message = f"Default tier is {actual_tier}, expected {expected_tier}"
        self.assertEqual(actual_tier, expected_tier, message)

    def test_get_or_create_updates_unclassified_tier(self):
        """Test that unclassified assets get updated tier."""
        # Create an unclassified asset
        unclassified = Asset.objects.create(
            ticker="BTC",
            name="Bitcoin",
            category=Asset.Category.CRYPTO,
            tier=Asset.Tier.UNCLASSIFIED,
        )

        # Get or create should update the tier
        asset = self.creator.get_or_create_asset("BTC")

        actual_tier = asset.tier
        expected_tier = Asset.Tier.TIER1
        message = f"Updated tier is {actual_tier}, expected {expected_tier}"
        self.assertEqual(actual_tier, expected_tier, message)

        # Verify it was actually saved
        asset.refresh_from_db()
        actual_tier = asset.tier
        message = f"Saved tier is {actual_tier}, expected {expected_tier}"
        self.assertEqual(actual_tier, expected_tier, message)

    def test_bulk_create_assets(self):
        """Test bulk creation of assets from trading pairs."""
        pair_names = ["XBTUSD", "ETHUSD", "ADAUSD", "DOGEUSD", "UNIEUR"]

        created_count = self.creator.bulk_create_assets(pair_names)

        # Should create unique tickers only (BTC, ETH, ADA, DOGE, UNI)
        actual_count = created_count
        expected_count = 5
        message = f"Created {actual_count} unique assets, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

        # Verify assets were created
        assets = Asset.objects.filter(ticker__in=["BTC", "ETH", "ADA", "DOGE", "UNI"])
        actual_db_count = assets.count()
        expected_db_count = 5
        message = f"Found {actual_db_count} assets in DB, expected {expected_db_count}"
        self.assertEqual(actual_db_count, expected_db_count, message)

    def test_bulk_create_assets_handles_duplicates(self):
        """Test that bulk_create handles existing assets."""
        # Pre-create some assets
        AssetFactory.create_crypto_asset(ticker="BTC")
        AssetFactory.create_crypto_asset(ticker="ETH")

        pair_names = ["XBTUSD", "ETHUSD", "ADAUSD"]  # BTC and ETH already exist

        created_count = self.creator.bulk_create_assets(pair_names)

        # Should count all unique tickers (3), even if some existed
        actual_count = created_count
        expected_count = 3
        message = f"Processed {actual_count} unique tickers, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

        # Only ADA should be newly created
        ada = Asset.objects.get(ticker="ADA")
        self.assertIsNotNone(ada, "ADA should be created")

    def test_bulk_create_populates_cache(self):
        """Test that bulk_create populates the asset cache."""
        pair_names = ["XBTUSD", "ETHUSD"]

        self.creator.bulk_create_assets(pair_names)

        # Cache should be populated - getting assets shouldn't query DB again
        btc = self.creator.get_or_create_asset("BTC")
        eth = self.creator.get_or_create_asset("ETH")

        actual_btc_ticker = btc.ticker
        expected_btc_ticker = "BTC"
        message = f"Cached BTC ticker is {actual_btc_ticker}, expected {expected_btc_ticker}"
        self.assertEqual(actual_btc_ticker, expected_btc_ticker, message)

        actual_eth_ticker = eth.ticker
        expected_eth_ticker = "ETH"
        message = f"Cached ETH ticker is {actual_eth_ticker}, expected {expected_eth_ticker}"
        self.assertEqual(actual_eth_ticker, expected_eth_ticker, message)

    def test_bulk_create_with_invalid_pairs(self):
        """Test that bulk_create handles invalid pairs gracefully."""
        pair_names = ["XBTUSD", "INVALID", "ETHUSD", "BADPAIR"]

        created_count = self.creator.bulk_create_assets(pair_names)

        # Should only create valid pairs (BTC, ETH)
        actual_count = created_count
        expected_count = 2
        message = f"Created {actual_count} assets from valid pairs, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)


class ParseOHLCVCSVTest(TestCase):
    """Test cases for the parse_ohlcv_csv function."""

    def test_parse_valid_csv(self):
        """Test parsing valid OHLCV CSV data."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow([1609459200, "29000.00", "29500.00", "28500.00", "29250.00", "1234567.89", "1500"])
            csv_writer.writerow([1609545600, "29250.00", "30000.00", "29000.00", "29750.00", "2345678.90", "2000"])
            temp_file = f.name

        try:
            # Parse the CSV
            rows = list(parse_ohlcv_csv(temp_file, interval_minutes=1440))

            actual_count = len(rows)
            expected_count = 2
            message = f"Parsed {actual_count} rows, expected {expected_count}"
            self.assertEqual(actual_count, expected_count, message)

            # Check first row
            first_row = rows[0]
            actual_timestamp = first_row["timestamp"]
            expected_timestamp = datetime.fromtimestamp(1609459200, tz=dt_timezone.utc)
            message = f"First row timestamp is {actual_timestamp}, expected {expected_timestamp}"
            self.assertEqual(actual_timestamp, expected_timestamp, message)

            actual_close = first_row["close"]
            expected_close = Decimal("29250.00")
            message = f"First row close is {actual_close}, expected {expected_close}"
            self.assertEqual(actual_close, expected_close, message)

            actual_interval = first_row["interval_minutes"]
            expected_interval = 1440
            message = f"Interval is {actual_interval}, expected {expected_interval}"
            self.assertEqual(actual_interval, expected_interval, message)

        finally:
            Path(temp_file).unlink()

    def test_parse_csv_with_missing_fields(self):
        """Test parsing CSV with missing optional fields."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_writer = csv.writer(f)
            # Row with no trade_count
            csv_writer.writerow([1609459200, "29000.00", "29500.00", "28500.00", "29250.00", "1234567.89"])
            # Row with empty volume
            csv_writer.writerow([1609545600, "29250.00", "30000.00", "29000.00", "29750.00", "", "2000"])
            temp_file = f.name

        try:
            rows = list(parse_ohlcv_csv(temp_file, interval_minutes=60))

            actual_count = len(rows)
            expected_count = 2
            message = f"Parsed {actual_count} rows with missing fields, expected {expected_count}"
            self.assertEqual(actual_count, expected_count, message)

            # Check first row has None trade_count
            first_row = rows[0]
            actual_trade_count = first_row["trade_count"]
            expected_trade_count = None
            message = f"Missing trade_count is {actual_trade_count}, expected {expected_trade_count}"
            self.assertEqual(actual_trade_count, expected_trade_count, message)

            # Check second row has None volume
            second_row = rows[1]
            actual_volume = second_row["volume"]
            expected_volume = None
            message = f"Empty volume is {actual_volume}, expected {expected_volume}"
            self.assertEqual(actual_volume, expected_volume, message)

        finally:
            Path(temp_file).unlink()

    def test_parse_csv_skips_invalid_rows(self):
        """Test that invalid rows are skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_writer = csv.writer(f)
            # Valid row
            csv_writer.writerow([1609459200, "29000.00", "29500.00", "28500.00", "29250.00", "1234567.89", "1500"])
            # Invalid: too few columns
            csv_writer.writerow([1609545600, "29250.00"])
            # Invalid: non-numeric timestamp
            csv_writer.writerow(["invalid", "29000.00", "29500.00", "28500.00", "29250.00", "1234567.89", "1500"])
            # Valid row
            csv_writer.writerow([1609632000, "30000.00", "30500.00", "29500.00", "30250.00", "3456789.01", "2500"])
            temp_file = f.name

        try:
            rows = list(parse_ohlcv_csv(temp_file, interval_minutes=1440))

            actual_count = len(rows)
            expected_count = 2
            message = f"Parsed {actual_count} valid rows (skipping invalid), expected {expected_count}"
            self.assertEqual(actual_count, expected_count, message)

        finally:
            Path(temp_file).unlink()

    def test_parse_empty_csv(self):
        """Test parsing empty CSV file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            # Empty file
            temp_file = f.name

        try:
            rows = list(parse_ohlcv_csv(temp_file, interval_minutes=1440))

            actual_count = len(rows)
            expected_count = 0
            message = f"Parsed {actual_count} rows from empty file, expected {expected_count}"
            self.assertEqual(actual_count, expected_count, message)

        finally:
            Path(temp_file).unlink()
