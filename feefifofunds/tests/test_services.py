"""
Unit tests for FeeFiFoFunds services.

Tests core services including QuestDBClient, DataSourceRouter, CoverageTracker,
GapDetector, and CompletenessReporter.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from freezegun import freeze_time

from feefifofunds.models import Asset, DataCoverageRange, GapRecord, IngestionJob
from feefifofunds.services.completeness_reporter import CompletenessReporter
from feefifofunds.services.coverage_tracker import CoverageTracker
from feefifofunds.services.data_source_router import DataSourceRouter
from feefifofunds.services.gap_detector import IntegratedGapDetector
from feefifofunds.services.questdb_client import QuestDBClient


class TestQuestDBClient(TestCase):
    """Test QuestDBClient for SQL injection prevention."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = QuestDBClient(database="default")

    @patch("feefifofunds.services.questdb_client.connections")
    def test_execute_query_with_params(self, mock_connections):
        """Test parameterized query execution."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, "test")]
        mock_connections.__getitem__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

        query = "SELECT * FROM table WHERE id = %s"
        params = [123]

        result = self.client.execute_query(query, params)

        # Verify parameterized query was used
        mock_cursor.execute.assert_called_once_with(query, params)
        self.assertEqual(result, [(1, "test")])

    def test_validate_int_valid(self):
        """Test integer validation with valid input."""
        result = self.client._validate_int(123, "test_param")
        self.assertEqual(result, 123)

        # Test string conversion
        result = self.client._validate_int("456", "test_param")
        self.assertEqual(result, 456)

    def test_validate_int_invalid(self):
        """Test integer validation with invalid input."""
        with self.assertRaises(ValueError) as cm:
            self.client._validate_int("not_a_number", "test_param")
        self.assertIn("Invalid test_param", str(cm.exception))

        with self.assertRaises(ValueError):
            self.client._validate_int(None, "test_param")

    def test_validate_datetime(self):
        """Test datetime validation."""
        dt = datetime.now()
        result = self.client._validate_datetime(dt, "test_date")
        self.assertEqual(result, dt)

        with self.assertRaises(ValueError) as cm:
            self.client._validate_datetime("not_a_date", "test_date")
        self.assertIn("Invalid test_date", str(cm.exception))

    @patch("feefifofunds.services.questdb_client.connections")
    def test_get_date_range_for_asset(self, mock_connections):
        """Test getting date range with SQL injection prevention."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(datetime(2020, 1, 1), datetime(2024, 12, 31), 1000)]
        mock_connections.__getitem__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

        # Test with potentially malicious input
        asset_id = "1; DROP TABLE assetprice; --"

        # Should validate and convert to safe integer
        with self.assertRaises(ValueError):
            self.client.get_date_range_for_asset(asset_id, 1440)

        # Test with valid input
        result = self.client.get_date_range_for_asset(1, 1440)
        self.assertIsNotNone(result)


class TestDataSourceRouter(TestCase):
    """Test DataSourceRouter for intelligent routing."""

    def setUp(self):
        """Set up test fixtures."""
        self.router = DataSourceRouter(tier="TIER1", intervals=[60, 1440])
        # Create test asset
        self.asset = Asset.objects.create(
            ticker="XBTUSD",
            name="Bitcoin",
            tier="TIER1",
            category=Asset.Category.CRYPTO,
            active=True,
        )

    @freeze_time("2024-01-15")
    def test_calculate_api_cutoff_date(self):
        """Test API cutoff date calculation."""
        # Daily: 720 candles = ~2 years
        cutoff = self.router._calculate_api_cutoff_date(1440, 720)
        expected = datetime.now() - timedelta(minutes=1440 * 720)
        self.assertEqual(cutoff.date(), expected.date())

        # Hourly: 720 candles = 30 days
        cutoff = self.router._calculate_api_cutoff_date(60, 720)
        expected = datetime.now() - timedelta(minutes=60 * 720)
        self.assertEqual(cutoff.date(), expected.date())

    @patch("feefifofunds.services.data_source_router.glob.glob")
    def test_find_csv_files_for_asset(self, mock_glob):
        """Test CSV file discovery for assets."""
        mock_glob.return_value = [
            "/data/XBTUSD_1440.csv",
            "/data/XBTUSD_60.csv",
            "/data/ETHUSD_1440.csv",
        ]

        files = self.router._find_csv_files_for_asset(self.asset, 1440, self.router.csv_dir)
        self.assertEqual(len(files), 1)
        self.assertIn("XBTUSD_1440.csv", files[0])

    @freeze_time("2024-01-15")
    def test_create_ingestion_plan(self):
        """Test ingestion plan creation."""
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2024, 1, 15)

        # Mock CSV file discovery
        with patch.object(self.router, "_find_csv_files_for_asset") as mock_find:
            mock_find.return_value = ["/data/XBTUSD_1440_2020.csv"]

            plan = self.router.create_ingestion_plan(start_date, end_date)

            self.assertGreater(len(plan.csv_sources), 0)
            self.assertGreater(len(plan.api_sources), 0)

            # Check that old data goes to CSV, recent to API
            for source in plan.csv_sources:
                self.assertLess(source.date_range_end, datetime.now() - timedelta(days=700))

            for source in plan.api_sources:
                self.assertGreater(source.date_range_start, datetime.now() - timedelta(days=730))


class TestCoverageTracker(TestCase):
    """Test CoverageTracker for range management."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = CoverageTracker(database="default")
        self.asset = Asset.objects.create(
            ticker="XBTUSD",
            name="Bitcoin",
            tier="TIER1",
            category=Asset.Category.CRYPTO,
        )
        self.job = IngestionJob.objects.create(
            tier="TIER1",
            intervals=[1440],
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2024, 1, 1),
        )

    @patch("feefifofunds.services.coverage_tracker.QuestDBClient")
    def test_update_coverage_for_asset(self, mock_client_class):
        """Test coverage update for single asset."""
        # Mock QuestDB response
        mock_client = mock_client_class.return_value
        mock_client.get_date_range_for_asset.return_value = (
            datetime(2020, 1, 1),
            datetime(2024, 1, 1),
            1460,
        )

        coverage = self.tracker.update_coverage_for_asset(self.asset, 1440, "CSV")

        self.assertIsNotNone(coverage)
        self.assertEqual(coverage.asset, self.asset)
        self.assertEqual(coverage.interval_minutes, 1440)
        self.assertEqual(coverage.source, "CSV")

    def test_merge_overlapping_ranges(self):
        """Test merging of overlapping coverage ranges."""
        # Create overlapping ranges
        DataCoverageRange.objects.create(
            asset=self.asset,
            interval_minutes=1440,
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31),
            source="CSV",
            record_count=365,
        )

        DataCoverageRange.objects.create(
            asset=self.asset,
            interval_minutes=1440,
            start_date=datetime(2020, 12, 15),  # Overlaps with range1
            end_date=datetime(2021, 6, 30),
            source="CSV",
            record_count=200,
        )

        # Merge ranges
        DataCoverageRange.merge_overlapping_ranges(self.asset, 1440)

        # Should have only one merged range now
        ranges = DataCoverageRange.objects.filter(asset=self.asset, interval_minutes=1440)
        self.assertEqual(ranges.count(), 1)

        merged = ranges.first()
        self.assertEqual(merged.start_date, datetime(2020, 1, 1))
        self.assertEqual(merged.end_date, datetime(2021, 6, 30))


class TestIntegratedGapDetector(TestCase):
    """Test IntegratedGapDetector for gap detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.detector = IntegratedGapDetector()
        self.asset = Asset.objects.create(
            ticker="XBTUSD",
            name="Bitcoin",
            tier="TIER1",
            category=Asset.Category.CRYPTO,
        )

    @freeze_time("2024-01-15")
    def test_detect_gaps_for_asset(self):
        """Test gap detection for single asset."""
        # Create coverage with gaps
        DataCoverageRange.objects.create(
            asset=self.asset,
            interval_minutes=1440,
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 12, 31),
            source="CSV",
            record_count=365,
        )

        DataCoverageRange.objects.create(
            asset=self.asset,
            interval_minutes=1440,
            start_date=datetime(2021, 2, 1),  # Gap in January 2021
            end_date=datetime(2023, 12, 31),
            source="CSV",
            record_count=1000,
        )

        gaps = self.detector.detect_gaps_for_asset(
            self.asset,
            1440,
            expected_start=datetime(2020, 1, 1),
            expected_end=datetime(2024, 1, 15),
        )

        self.assertEqual(len(gaps), 2)  # January 2021 gap and 2024 gap

        # Check first gap (January 2021)
        gap1 = gaps[0]
        self.assertEqual(gap1.gap_start, datetime(2021, 1, 1))
        self.assertEqual(gap1.gap_end, datetime(2021, 1, 31, 23, 59, 59, 999999))
        self.assertFalse(gap1.is_api_fillable)  # Too old for API

        # Check second gap (2024)
        gap2 = gaps[1]
        self.assertEqual(gap2.gap_start, datetime(2024, 1, 1))
        self.assertTrue(gap2.is_api_fillable)  # Recent enough for API

    def test_classify_gap_fillability(self):
        """Test gap fillability classification."""
        # Recent gap (should be API fillable)
        recent_gap = self.detector._create_gap_record(
            asset=self.asset,
            interval_minutes=1440,
            start=datetime.now() - timedelta(days=10),
            end=datetime.now(),
            now=datetime.now(),
        )
        self.assertTrue(recent_gap.is_api_fillable)
        self.assertEqual(recent_gap.status, GapRecord.Status.DETECTED)

        # Old gap (should not be API fillable)
        old_gap = self.detector._create_gap_record(
            asset=self.asset,
            interval_minutes=1440,
            start=datetime.now() - timedelta(days=1000),
            end=datetime.now() - timedelta(days=900),
            now=datetime.now(),
        )
        self.assertFalse(old_gap.is_api_fillable)
        self.assertEqual(old_gap.status, GapRecord.Status.UNFILLABLE)
        self.assertIsNotNone(old_gap.required_csv_file)


class TestCompletenessReporter(TestCase):
    """Test CompletenessReporter for metrics generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.reporter = CompletenessReporter(database="default")
        self.asset = Asset.objects.create(
            ticker="XBTUSD",
            name="Bitcoin",
            tier="TIER1",
            category=Asset.Category.CRYPTO,
        )

    @patch("feefifofunds.services.completeness_reporter.QuestDBClient")
    def test_generate_report(self, mock_client_class):
        """Test completeness report generation."""
        # Mock QuestDB candle counts
        mock_client = mock_client_class.return_value
        mock_client.count_candles.return_value = 1000

        # Create some gaps
        GapRecord.objects.create(
            asset=self.asset,
            interval_minutes=1440,
            gap_start=datetime(2021, 1, 1),
            gap_end=datetime(2021, 1, 31),
            missing_candles=31,
            is_api_fillable=False,
            status=GapRecord.Status.UNFILLABLE,
        )

        report = self.reporter.generate_report(
            tier="TIER1",
            intervals=[1440],
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2024, 1, 1),
        )

        self.assertIsNotNone(report)
        self.assertEqual(report.tier, "TIER1")
        self.assertGreater(report.total_assets, 0)
        self.assertEqual(report.total_gaps, 1)
        self.assertLess(report.overall_completeness_pct, 100.0)

    def test_calculate_expected_candles(self):
        """Test expected candle calculation."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31, 23, 59, 59)

        # Daily candles for January
        expected = self.reporter._calculate_expected_candles(start, end, 1440)
        self.assertEqual(expected, 31)

        # Hourly candles for one day
        expected = self.reporter._calculate_expected_candles(
            datetime(2024, 1, 1),
            datetime(2024, 1, 1, 23, 59, 59),
            60,
        )
        self.assertEqual(expected, 24)


class TestValidators(TestCase):
    """Test input validators."""

    def test_ingestion_config_validation(self):
        """Test IngestionConfig validation."""
        from feefifofunds.validators import IngestionConfig

        # Valid config
        config = IngestionConfig(
            tier="TIER1",
            intervals=[60, 1440],
            lookback_days=7,
            max_gaps_per_asset=10,
        )
        self.assertEqual(config.tier, "TIER1")

        # Invalid tier
        with self.assertRaises(ValueError):
            IngestionConfig(tier="INVALID", intervals=[60])

        # Invalid interval
        with self.assertRaises(ValueError):
            IngestionConfig(tier="TIER1", intervals=[999])

        # Invalid date range
        with self.assertRaises(ValueError):
            IngestionConfig(
                tier="TIER1",
                intervals=[60],
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2023, 1, 1),  # Before start
            )


class TestDecorators(TestCase):
    """Test decorators for rate limiting and retry."""

    def test_rate_limit_decorator(self):
        """Test rate limiting decorator."""
        from feefifofunds.decorators import rate_limit

        call_times = []

        @rate_limit(calls_per_second=2.0)  # Max 2 calls per second
        def test_func():
            call_times.append(datetime.now())
            return "success"

        # Make 3 rapid calls
        start = datetime.now()
        for _ in range(3):
            test_func()

        # Should have taken at least 1 second for 3 calls at 2/sec
        elapsed = (datetime.now() - start).total_seconds()
        self.assertGreaterEqual(elapsed, 1.0)

        # Check spacing between calls
        for i in range(1, len(call_times)):
            gap = (call_times[i] - call_times[i - 1]).total_seconds()
            self.assertGreaterEqual(gap, 0.45)  # Allow small margin

    def test_retry_with_backoff_decorator(self):
        """Test retry decorator with exponential backoff."""
        from feefifofunds.decorators import retry_with_backoff

        call_count = [0]

        @retry_with_backoff(max_attempts=3, min_wait=0.01, max_wait=0.1)
        def test_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Test error")
            return "success"

        result = test_func()
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 3)  # Should retry twice

    def test_cached_result_decorator(self):
        """Test caching decorator."""
        from feefifofunds.decorators import cached_result

        call_count = [0]

        @cached_result(timeout=60)
        def test_func(value):
            call_count[0] += 1
            return value * 2

        # First call should execute function
        result1 = test_func(5)
        self.assertEqual(result1, 10)
        self.assertEqual(call_count[0], 1)

        # Second call should use cache
        result2 = test_func(5)
        self.assertEqual(result2, 10)
        self.assertEqual(call_count[0], 1)  # No additional call

        # Different argument should execute function
        result3 = test_func(10)
        self.assertEqual(result3, 20)
        self.assertEqual(call_count[0], 2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
