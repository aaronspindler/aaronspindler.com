import shutil
import tempfile
from pathlib import Path
from unittest import skipUnless
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase

from feefifofunds.models import Asset, AssetPrice
from feefifofunds.services.kraken import KrakenAssetCreator, KrakenPairParser
from feefifofunds.services.sequential_ingestor import SequentialIngestor


class SequentialIngestorUnitTest(TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.ohlcv_dir = self.test_dir / "Kraken_OHLCVT"
        self.ohlcv_dir.mkdir(parents=True)

        sample_data_dir = Path(__file__).parent / "data" / "Kraken_OHLCVT"
        for csv_file in sample_data_dir.glob("*.csv"):
            shutil.copy(csv_file, self.ohlcv_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_file_discovery_finds_all_csv_files(self):
        ingestor = SequentialIngestor(data_dir=str(self.test_dir))
        files = ingestor.discover_files(tier_filter=None, file_type_filter="ohlcv")

        actual_count = len(files)
        expected_count = 4
        message = f"Found {actual_count} files, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

        for filepath, file_type, _ticker in files:
            actual_file_type = file_type
            expected_file_type = "ohlcv"
            message = f"File type is {actual_file_type}, expected {expected_file_type}"
            self.assertEqual(actual_file_type, expected_file_type, message)

            self.assertIsInstance(filepath, Path)
            self.assertTrue(filepath.exists())

    def test_file_discovery_filters_by_tier(self):
        ingestor = SequentialIngestor(data_dir=str(self.test_dir))

        tier1_files = ingestor.discover_files(tier_filter="TIER1", file_type_filter="ohlcv")
        actual_count = len(tier1_files)
        expected_count = 4
        message = f"Found {actual_count} TIER1 files, expected {expected_count} (all test files are BTC which is TIER1)"
        self.assertEqual(actual_count, expected_count, message)

        tier2_files = ingestor.discover_files(tier_filter="TIER2", file_type_filter="ohlcv")
        actual_count = len(tier2_files)
        expected_count = 0
        message = f"Found {actual_count} TIER2 files, expected {expected_count} (no TIER2 assets in test data)"
        self.assertEqual(actual_count, expected_count, message)

        all_files = ingestor.discover_files(tier_filter="ALL", file_type_filter="ohlcv")
        actual_count = len(all_files)
        expected_count = 4
        message = f"Found {actual_count} files with ALL filter, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

    def test_file_discovery_filters_by_interval(self):
        ingestor = SequentialIngestor(data_dir=str(self.test_dir))

        daily_files = ingestor.discover_files(tier_filter=None, file_type_filter="ohlcv", interval_filter=[1440])
        actual_count = len(daily_files)
        expected_count = 2
        message = f"Found {actual_count} daily files (1440 interval), expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

        for filepath, _, _ in daily_files:
            self.assertIn("1440", filepath.name)

        twelve_hour_files = ingestor.discover_files(tier_filter=None, file_type_filter="ohlcv", interval_filter=[720])
        actual_count = len(twelve_hour_files)
        expected_count = 2
        message = f"Found {actual_count} 12-hour files (720 interval), expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

        for filepath, _, _ in twelve_hour_files:
            self.assertIn("720", filepath.name)

        multi_interval_files = ingestor.discover_files(
            tier_filter=None, file_type_filter="ohlcv", interval_filter=[720, 1440]
        )
        actual_count = len(multi_interval_files)
        expected_count = 4
        message = f"Found {actual_count} files with multiple intervals, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

    def test_filename_parsing(self):
        test_cases = [
            ("XBTUSD_1440.csv", "XBTUSD", 1440),
            ("XBTCAD_720.csv", "XBTCAD", 720),
            ("XBTUSD_720.csv", "XBTUSD", 720),
            ("XBTCAD_1440.csv", "XBTCAD", 1440),
        ]

        for filename, expected_pair, expected_interval in test_cases:
            stem = filename.replace(".csv", "")
            parts = stem.split("_")

            actual_pair = parts[0]
            actual_interval = int(parts[1])

            pair_message = f"Parsed pair is {actual_pair}, expected {expected_pair}"
            self.assertEqual(actual_pair, expected_pair, pair_message)

            interval_message = f"Parsed interval is {actual_interval}, expected {expected_interval}"
            self.assertEqual(actual_interval, expected_interval, interval_message)

    def test_pair_parsing(self):
        test_cases = [
            ("XBTUSD", "BTC", "USD"),
            ("XBTCAD", "BTC", "CAD"),
            ("XXBTZUSD", "BTC", "USD"),  # Alternative Kraken format
        ]

        for pair_name, expected_base, expected_quote in test_cases:
            actual_base, actual_quote = KrakenPairParser.parse_pair(pair_name)

            base_message = f"Parsed base ticker is {actual_base}, expected {expected_base}"
            self.assertEqual(actual_base, expected_base, base_message)

            quote_message = f"Parsed quote currency is {actual_quote}, expected {expected_quote}"
            self.assertEqual(actual_quote, expected_quote, quote_message)

    def test_asset_tier_determination(self):
        tier1_tickers = ["BTC", "ETH", "USDT", "USDC"]
        for ticker in tier1_tickers:
            actual_tier = KrakenAssetCreator.determine_tier(ticker)
            expected_tier = Asset.Tier.TIER1
            message = f"Ticker {ticker} classified as {actual_tier}, expected {expected_tier}"
            self.assertEqual(actual_tier, expected_tier, message)

        tier2_tickers = ["UNI", "ALGO", "AAVE"]
        for ticker in tier2_tickers:
            actual_tier = KrakenAssetCreator.determine_tier(ticker)
            expected_tier = Asset.Tier.TIER2
            message = f"Ticker {ticker} classified as {actual_tier}, expected {expected_tier}"
            self.assertEqual(actual_tier, expected_tier, message)

        tier3_tickers = ["1INCH", "CRV", "BAT"]
        for ticker in tier3_tickers:
            actual_tier = KrakenAssetCreator.determine_tier(ticker)
            expected_tier = Asset.Tier.TIER3
            message = f"Ticker {ticker} classified as {actual_tier}, expected {expected_tier}"
            self.assertEqual(actual_tier, expected_tier, message)

        tier4_tickers = ["UNKNOWN", "RANDOM", "TEST"]
        for ticker in tier4_tickers:
            actual_tier = KrakenAssetCreator.determine_tier(ticker)
            expected_tier = Asset.Tier.TIER4
            message = f"Ticker {ticker} classified as {actual_tier}, expected {expected_tier}"
            self.assertEqual(actual_tier, expected_tier, message)

    def test_asset_creation(self):
        asset_creator = KrakenAssetCreator()

        btc_ticker = "BTC"
        btc_asset = asset_creator.get_or_create_asset(btc_ticker)

        actual_ticker = btc_asset.ticker
        expected_ticker = btc_ticker
        ticker_message = f"Asset ticker is {actual_ticker}, expected {expected_ticker}"
        self.assertEqual(actual_ticker, expected_ticker, ticker_message)

        actual_category = btc_asset.category
        expected_category = Asset.Category.CRYPTO
        category_message = f"Asset category is {actual_category}, expected {expected_category}"
        self.assertEqual(actual_category, expected_category, category_message)

        actual_tier = btc_asset.tier
        expected_tier = Asset.Tier.TIER1
        tier_message = f"Asset tier is {actual_tier}, expected {expected_tier}"
        self.assertEqual(actual_tier, expected_tier, tier_message)

        usd_ticker = "USD"
        usd_asset = asset_creator.get_or_create_asset(usd_ticker)

        actual_ticker = usd_asset.ticker
        expected_ticker = usd_ticker
        ticker_message = f"Asset ticker is {actual_ticker}, expected {expected_ticker}"
        self.assertEqual(actual_ticker, expected_ticker, ticker_message)

        actual_category = usd_asset.category
        expected_category = Asset.Category.CURRENCY
        category_message = f"Asset category is {actual_category}, expected {expected_category}"
        self.assertEqual(actual_category, expected_category, category_message)

    @patch("feefifofunds.services.sequential_ingestor.Sender")
    def test_ingestion_with_mocked_ilp(self, mock_sender_class):
        mock_sender_instance = MagicMock()
        mock_sender_class.from_conf.return_value.__enter__.return_value = mock_sender_instance

        asset_creator = KrakenAssetCreator()
        btc_asset = asset_creator.get_or_create_asset("BTC")

        ingestor = SequentialIngestor(data_dir=str(self.test_dir))
        ingestor.connect_ilp()
        ingestor.load_asset_cache()

        test_file = self.ohlcv_dir / "XBTUSD_1440.csv"
        records_inserted = ingestor.process_ohlcv_file(
            filepath=test_file,
            asset=btc_asset,
            interval_minutes=1440,
            quote_currency="USD",
            total_lines=0,
            progress_callback=None,
        )

        actual_records = records_inserted
        expected_records_min = 4000
        message = f"Inserted {actual_records} records, expected at least {expected_records_min}"
        self.assertGreater(actual_records, expected_records_min, message)

        actual_call_count = mock_sender_instance.row.call_count
        expected_call_count = records_inserted
        message = f"ILP sender called {actual_call_count} times, expected {expected_call_count}"
        self.assertEqual(actual_call_count, expected_call_count, message)

        if mock_sender_instance.row.call_count > 0:
            first_call_args = mock_sender_instance.row.call_args_list[0]
            actual_table_name = first_call_args[0][0]
            expected_table_name = "assetprice"
            message = f"ILP table name is {actual_table_name}, expected {expected_table_name}"
            self.assertEqual(actual_table_name, expected_table_name, message)

        ingestor.disconnect_ilp()

    def test_empty_file_detection(self):
        ingestor = SequentialIngestor(data_dir=str(self.test_dir))

        empty_file = self.ohlcv_dir / "EMPTY_1440.csv"
        empty_file.touch()

        actual_is_empty = ingestor._check_empty_file(empty_file)
        expected_is_empty = True
        message = f"Empty file detection returned {actual_is_empty}, expected {expected_is_empty}"
        self.assertEqual(actual_is_empty, expected_is_empty, message)

        header_only_file = self.ohlcv_dir / "HEADER_ONLY_1440.csv"
        header_only_file.write_text("timestamp,open,high,low,close,volume,trade_count\n")

        actual_is_empty = ingestor._check_empty_file(header_only_file)
        expected_is_empty = True
        message = f"Header-only file detection returned {actual_is_empty}, expected {expected_is_empty}"
        self.assertEqual(actual_is_empty, expected_is_empty, message)

        real_file = self.ohlcv_dir / "XBTUSD_1440.csv"
        actual_is_empty = ingestor._check_empty_file(real_file)
        expected_is_empty = False
        message = f"Real file detection returned {actual_is_empty}, expected {expected_is_empty}"
        self.assertEqual(actual_is_empty, expected_is_empty, message)


@skipUnless(settings.DATABASES.get("questdb"), "QuestDB not configured for integration tests")
class SequentialIngestorIntegrationTest(TestCase):
    databases = ["default", "questdb"]

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.ohlcv_dir = self.test_dir / "Kraken_OHLCVT"
        self.ohlcv_dir.mkdir(parents=True)

        sample_data_dir = Path(__file__).parent / "data" / "Kraken_OHLCVT"
        for csv_file in sample_data_dir.glob("*.csv"):
            shutil.copy(csv_file, self.ohlcv_dir)

        Asset.objects.filter(ticker__in=["BTC", "USD", "CAD"]).delete()

        try:
            AssetPrice.objects.using("questdb").all().delete()
        except Exception:
            # Ignore errors if no test data exists to clean up
            pass

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

        Asset.objects.filter(ticker__in=["BTC", "USD", "CAD"]).delete()

    def test_full_ingestion_pipeline(self):
        ingestor = SequentialIngestor(data_dir=str(self.test_dir))
        ingestor.connect_ilp()
        ingestor.load_asset_cache()

        files = ingestor.discover_files(tier_filter="TIER1", file_type_filter="ohlcv")

        for filepath, file_type, _ in files:
            success, records_processed, error = ingestor.process_file(
                filepath=filepath, file_type=file_type, progress_callback=None
            )

            actual_success = success
            expected_success = True
            message = f"File {filepath.name} processing returned {actual_success}, expected {expected_success}"
            self.assertEqual(actual_success, expected_success, message)

            if error:
                message = f"File {filepath.name} processing failed with error: {error}"
                self.assertIsNone(error, message)

            actual_records = records_processed
            expected_records_min = 100
            message = (
                f"File {filepath.name} processed {actual_records} records, expected at least {expected_records_min}"
            )
            self.assertGreater(actual_records, expected_records_min, message)

        ingestor.disconnect_ilp()

        btc_asset = Asset.objects.filter(ticker="BTC").first()
        self.assertIsNotNone(btc_asset, "BTC asset should be created")

        actual_tier = btc_asset.tier
        expected_tier = Asset.Tier.TIER1
        message = f"BTC asset tier is {actual_tier}, expected {expected_tier}"
        self.assertEqual(actual_tier, expected_tier, message)

        price_count = AssetPrice.objects.using("questdb").filter(asset_id=btc_asset.id).count()

        actual_count = price_count
        expected_count_min = 20000
        message = f"Found {actual_count} price records in QuestDB, expected at least {expected_count_min}"
        self.assertGreater(actual_count, expected_count_min, message)

        ingested_dir = self.test_dir / "ingested" / "ohlcv"
        ingested_files = list(ingested_dir.glob("*.csv"))

        actual_ingested_count = len(ingested_files)
        expected_ingested_count = 4
        message = f"Found {actual_ingested_count} ingested files, expected {expected_ingested_count}"
        self.assertEqual(actual_ingested_count, expected_ingested_count, message)

    def test_idempotency(self):
        ingestor1 = SequentialIngestor(data_dir=str(self.test_dir))
        ingestor1.connect_ilp()
        ingestor1.load_asset_cache()

        files = ingestor1.discover_files(tier_filter="TIER1", file_type_filter="ohlcv", interval_filter=[1440])

        total_records_first = 0
        for filepath, file_type, _ in files:
            success, records_processed, _ = ingestor1.process_file(
                filepath=filepath, file_type=file_type, progress_callback=None
            )
            if success:
                total_records_first += records_processed

        ingestor1.disconnect_ilp()

        btc_asset = Asset.objects.get(ticker="BTC")
        first_count = AssetPrice.objects.using("questdb").filter(asset_id=btc_asset.id).count()

        sample_data_dir = Path(__file__).parent / "data" / "Kraken_OHLCVT"
        for csv_file in sample_data_dir.glob("*1440.csv"):
            shutil.copy(csv_file, self.ohlcv_dir)

        ingestor2 = SequentialIngestor(data_dir=str(self.test_dir))
        ingestor2.connect_ilp()
        ingestor2.load_asset_cache()

        files = ingestor2.discover_files(tier_filter="TIER1", file_type_filter="ohlcv", interval_filter=[1440])

        total_records_second = 0
        for filepath, file_type, _ in files:
            success, records_processed, _ = ingestor2.process_file(
                filepath=filepath, file_type=file_type, progress_callback=None
            )
            if success:
                total_records_second += records_processed

        ingestor2.disconnect_ilp()

        second_count = AssetPrice.objects.using("questdb").filter(asset_id=btc_asset.id).count()

        actual_first = total_records_first
        actual_second = total_records_second
        message = f"First ingestion processed {actual_first} records, second processed {actual_second}"
        self.assertEqual(actual_first, actual_second, message)

        actual_second_count = second_count
        expected_min = first_count
        message = f"Second ingestion resulted in {actual_second_count} total records, expected at least {expected_min}"
        self.assertGreaterEqual(actual_second_count, expected_min, message)

    def test_empty_directory(self):
        empty_dir = Path(tempfile.mkdtemp())
        empty_ohlcv_dir = empty_dir / "Kraken_OHLCVT"
        empty_ohlcv_dir.mkdir(parents=True)

        try:
            ingestor = SequentialIngestor(data_dir=str(empty_dir))
            files = ingestor.discover_files(tier_filter="TIER1", file_type_filter="ohlcv")

            actual_count = len(files)
            expected_count = 0
            message = f"Empty directory returned {actual_count} files, expected {expected_count}"
            self.assertEqual(actual_count, expected_count, message)

            # Verify ingestor can handle empty file list
            ingestor.connect_ilp()
            ingestor.load_asset_cache()

            for filepath, file_type, _ in files:
                _, _, _ = ingestor.process_file(filepath=filepath, file_type=file_type, progress_callback=None)
                self.fail(f"Should not process any files in empty directory, but processed {filepath.name}")

            ingestor.disconnect_ilp()

        finally:
            if empty_dir.exists():
                shutil.rmtree(empty_dir)
