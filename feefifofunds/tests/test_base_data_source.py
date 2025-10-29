"""
Unit tests for BaseDataSource abstract class.

Tests cover rate limiting, error handling, caching, monitoring, and DTO validation.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from django.core.cache import cache
from django.test import TestCase

from feefifofunds.models import DataSource, DataSync
from feefifofunds.services.data_sources import (
    BaseDataSource,
    DataSourceError,
    FundDataDTO,
    HoldingDataDTO,
    PerformanceDataDTO,
    RateLimitError,
)


class ConcreteDataSource(BaseDataSource):
    """Concrete implementation for testing."""

    name = "test_source"
    display_name = "Test Data Source"
    base_url = "https://api.test.com"
    requires_api_key = False
    rate_limit_requests = 10
    rate_limit_period = 60

    def fetch_fund_info(self, ticker: str) -> FundDataDTO:
        return FundDataDTO(ticker=ticker, name="Test Fund", source=self.name)

    def fetch_historical_prices(self, ticker: str, start_date: date, end_date: date, interval: str = "1D") -> list:
        return []

    def fetch_holdings(self, ticker: str) -> list:
        return []


class BaseDataSourceTestCase(TestCase):
    """Test cases for BaseDataSource functionality."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()
        DataSource.objects.all().delete()
        self.data_source = ConcreteDataSource()

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    # Rate Limiting Tests

    def test_can_make_request_initially_true(self):
        """Test that can_make_request returns True initially."""
        self.assertTrue(self.data_source.can_make_request())

    def test_can_make_request_false_after_limit_reached(self):
        """Test that can_make_request returns False after rate limit reached."""
        # Make requests up to the limit
        for _ in range(self.data_source.rate_limit_requests):
            self.data_source.record_request(success=True)

        # Next check should return False
        self.assertFalse(self.data_source.can_make_request())

    def test_record_request_increments_counter(self):
        """Test that record_request increments requests_today."""
        initial_count = self.data_source.data_source_model.requests_today

        self.data_source.record_request(success=True)
        self.data_source.data_source_model.refresh_from_db()

        self.assertEqual(self.data_source.data_source_model.requests_today, initial_count + 1)

    def test_record_request_success_updates_last_successful_sync(self):
        """Test that successful request updates last_successful_sync."""
        self.data_source.record_request(success=True)
        self.data_source.data_source_model.refresh_from_db()

        self.assertIsNotNone(self.data_source.data_source_model.last_successful_sync)

    def test_record_request_failure_increments_consecutive_failures(self):
        """Test that failed request increments consecutive_failures."""
        initial_failures = self.data_source.data_source_model.consecutive_failures

        self.data_source.record_request(success=False, error_message="Test error")
        self.data_source.data_source_model.refresh_from_db()

        self.assertEqual(
            self.data_source.data_source_model.consecutive_failures,
            initial_failures + 1,
        )

    def test_record_request_failure_stores_error_message(self):
        """Test that failed request stores error message."""
        error_msg = "Test error message"
        self.data_source.record_request(success=False, error_message=error_msg)
        self.data_source.data_source_model.refresh_from_db()

        self.assertEqual(self.data_source.data_source_model.last_error, error_msg)

    def test_auto_disable_after_five_consecutive_failures(self):
        """Test that data source auto-disables after 5 consecutive failures."""
        # Record 5 failures
        for _ in range(5):
            self.data_source.record_request(success=False, error_message="Error")

        self.data_source.data_source_model.refresh_from_db()

        # Status should be ERROR and can_make_request should return False
        self.assertEqual(self.data_source.data_source_model.status, DataSource.Status.ERROR)
        self.assertFalse(self.data_source.can_make_request())

    def test_consecutive_failures_reset_on_success(self):
        """Test that consecutive_failures resets to 0 on successful request."""
        # Record some failures
        for _ in range(3):
            self.data_source.record_request(success=False, error_message="Error")

        # Record success
        self.data_source.record_request(success=True)
        self.data_source.data_source_model.refresh_from_db()

        self.assertEqual(self.data_source.data_source_model.consecutive_failures, 0)

    def test_reliability_score_decreases_on_failure(self):
        """Test that reliability_score decreases on failed request."""
        initial_score = self.data_source.data_source_model.reliability_score

        self.data_source.record_request(success=False, error_message="Error")
        self.data_source.data_source_model.refresh_from_db()

        self.assertLess(self.data_source.data_source_model.reliability_score, initial_score)

    # HTTP Request Tests

    @patch("feefifofunds.services.data_sources.base.requests.Session.get")
    def test_make_request_success(self, mock_get):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        result = self.data_source._make_request("https://api.test.com/endpoint")

        self.assertEqual(result, {"data": "test"})
        mock_get.assert_called_once()

    @patch("feefifofunds.services.data_sources.base.requests.Session.get")
    def test_make_request_http_error(self, mock_get):
        """Test HTTP error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_get.return_value = mock_response

        with self.assertRaises(DataSourceError):
            self.data_source._make_request("https://api.test.com/endpoint")

    @patch("feefifofunds.services.data_sources.base.requests.Session.get")
    def test_make_request_rate_limit_error(self, mock_get):
        """Test 429 rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        error = requests.exceptions.HTTPError()
        error.response = mock_response
        mock_response.raise_for_status.side_effect = error
        mock_get.return_value = mock_response

        with self.assertRaises(RateLimitError):
            self.data_source._make_request("https://api.test.com/endpoint")

    @patch("feefifofunds.services.data_sources.base.requests.Session.get")
    def test_make_request_timeout(self, mock_get):
        """Test request timeout handling."""
        mock_get.side_effect = requests.exceptions.Timeout()

        with self.assertRaises(DataSourceError):
            self.data_source._make_request("https://api.test.com/endpoint")

    @patch("feefifofunds.services.data_sources.base.requests.Session.get")
    def test_make_request_invalid_json(self, mock_get):
        """Test invalid JSON response handling."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        with self.assertRaises(DataSourceError):
            self.data_source._make_request("https://api.test.com/endpoint")

    @patch("feefifofunds.services.data_sources.base.requests.Session.get")
    def test_make_request_records_success(self, mock_get):
        """Test that successful request is recorded."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        initial_count = self.data_source.data_source_model.requests_today

        self.data_source._make_request("https://api.test.com/endpoint")
        self.data_source.data_source_model.refresh_from_db()

        self.assertEqual(self.data_source.data_source_model.requests_today, initial_count + 1)

    @patch("feefifofunds.services.data_sources.base.requests.Session.get")
    def test_make_request_records_failure(self, mock_get):
        """Test that failed request is recorded."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        with self.assertRaises(DataSourceError):
            self.data_source._make_request("https://api.test.com/endpoint")

        self.data_source.data_source_model.refresh_from_db()
        self.assertIsNotNone(self.data_source.data_source_model.last_error)

    # Caching Tests

    def test_get_cached_or_fetch_cache_miss(self):
        """Test cache miss triggers fetch function."""
        fetch_func = Mock(return_value={"data": "test"})
        cache_key = "test_key"

        result = self.data_source._get_cached_or_fetch(cache_key, fetch_func, cache_timeout=60)

        self.assertEqual(result, {"data": "test"})
        fetch_func.assert_called_once()

    def test_get_cached_or_fetch_cache_hit(self):
        """Test cache hit skips fetch function."""
        cache_key = "test_key"
        cached_data = {"data": "cached"}
        cache.set(cache_key, cached_data, 60)

        fetch_func = Mock()

        result = self.data_source._get_cached_or_fetch(cache_key, fetch_func, cache_timeout=60)

        self.assertEqual(result, cached_data)
        fetch_func.assert_not_called()

    def test_get_cached_or_fetch_stores_in_cache(self):
        """Test that fetched data is stored in cache."""
        cache_key = "test_key"
        fetch_func = Mock(return_value={"data": "test"})

        self.data_source._get_cached_or_fetch(cache_key, fetch_func, cache_timeout=60)

        cached_value = cache.get(cache_key)
        self.assertEqual(cached_value, {"data": "test"})

    # Data Validation Tests

    def test_validate_data_none_returns_false(self):
        """Test that None data is invalid."""
        self.assertFalse(self.data_source.validate_data(None))

    def test_validate_data_empty_list_returns_false(self):
        """Test that empty list is invalid."""
        self.assertFalse(self.data_source.validate_data([]))

    def test_validate_data_valid_data_returns_true(self):
        """Test that valid data returns True."""
        self.assertTrue(self.data_source.validate_data({"data": "test"}))
        self.assertTrue(self.data_source.validate_data([1, 2, 3]))

    # Feature Support Tests

    def test_supports_feature_historical(self):
        """Test checking for historical data support."""
        self.data_source.data_source_model.supports_historical_data = True
        self.data_source.data_source_model.save()

        self.assertTrue(self.data_source.supports_feature("historical"))

    def test_supports_feature_realtime(self):
        """Test checking for realtime data support."""
        self.data_source.data_source_model.supports_realtime_data = False
        self.data_source.data_source_model.save()

        self.assertFalse(self.data_source.supports_feature("realtime"))

    # DataSync Record Tests

    def test_create_sync_record(self):
        """Test creating DataSync record."""
        sync = self.data_source.create_sync_record(
            sync_type=DataSync.SyncType.FUND_INFO,
            request_params={"ticker": "VTI"},
        )

        self.assertIsNotNone(sync)
        self.assertEqual(sync.data_source, self.data_source.data_source_model)
        self.assertEqual(sync.sync_type, DataSync.SyncType.FUND_INFO)
        self.assertEqual(sync.status, DataSync.Status.IN_PROGRESS)


class FundDataDTOTestCase(TestCase):
    """Test cases for FundDataDTO validation."""

    def test_fund_data_dto_required_fields(self):
        """Test that required fields are validated."""
        # Should succeed with required fields
        dto = FundDataDTO(ticker="VTI", name="Vanguard Total Stock Market ETF")
        self.assertEqual(dto.ticker, "VTI")

        # Should fail without ticker
        with self.assertRaises(ValueError):
            FundDataDTO(ticker="", name="Test Fund")

        # Should fail without name
        with self.assertRaises(ValueError):
            FundDataDTO(ticker="VTI", name="")

    def test_fund_data_dto_decimal_conversion(self):
        """Test automatic conversion to Decimal for financial fields."""
        dto = FundDataDTO(
            ticker="VTI",
            name="Test Fund",
            expense_ratio=0.03,  # float
            current_price=250.50,  # float
            aum=1000000,  # int
        )

        self.assertIsInstance(dto.expense_ratio, Decimal)
        self.assertIsInstance(dto.current_price, Decimal)
        self.assertIsInstance(dto.aum, Decimal)

    def test_fund_data_dto_default_values(self):
        """Test default values for optional fields."""
        dto = FundDataDTO(ticker="VTI", name="Test Fund")

        self.assertEqual(dto.currency, "USD")
        self.assertEqual(dto.source, "unknown")
        self.assertIsInstance(dto.fetched_at, datetime)


class PerformanceDataDTOTestCase(TestCase):
    """Test cases for PerformanceDataDTO validation."""

    def test_performance_data_dto_required_fields(self):
        """Test that required fields are validated."""
        # Should succeed
        dto = PerformanceDataDTO(ticker="VTI", date=date(2025, 1, 15), close_price=Decimal("250.50"))
        self.assertEqual(dto.ticker, "VTI")

        # Should fail without ticker
        with self.assertRaises(ValueError):
            PerformanceDataDTO(ticker="", date=date(2025, 1, 15), close_price=Decimal("250.50"))

        # Should fail without date
        with self.assertRaises(ValueError):
            PerformanceDataDTO(ticker="VTI", date=None, close_price=Decimal("250.50"))

        # Should fail without close_price
        with self.assertRaises(ValueError):
            PerformanceDataDTO(ticker="VTI", date=date(2025, 1, 15), close_price=None)

    def test_performance_data_dto_decimal_conversion(self):
        """Test automatic conversion to Decimal for price fields."""
        dto = PerformanceDataDTO(
            ticker="VTI",
            date=date(2025, 1, 15),
            close_price=250.50,  # float
            open_price=249.00,  # float
            high_price=251.00,  # float
            low_price=248.50,  # float
        )

        self.assertIsInstance(dto.close_price, Decimal)
        self.assertIsInstance(dto.open_price, Decimal)
        self.assertIsInstance(dto.high_price, Decimal)
        self.assertIsInstance(dto.low_price, Decimal)

    def test_performance_data_dto_interval_default(self):
        """Test default interval value."""
        dto = PerformanceDataDTO(ticker="VTI", date=date(2025, 1, 15), close_price=Decimal("250.50"))

        self.assertEqual(dto.interval, "1D")


class HoldingDataDTOTestCase(TestCase):
    """Test cases for HoldingDataDTO validation."""

    def test_holding_data_dto_required_fields(self):
        """Test that required fields are validated."""
        # Should succeed
        dto = HoldingDataDTO(ticker="AAPL", name="Apple Inc.", weight=Decimal("5.25"))
        self.assertEqual(dto.ticker, "AAPL")

        # Should fail without ticker
        with self.assertRaises(ValueError):
            HoldingDataDTO(ticker="", name="Apple Inc.", weight=Decimal("5.25"))

        # Should fail without name
        with self.assertRaises(ValueError):
            HoldingDataDTO(ticker="AAPL", name="", weight=Decimal("5.25"))

        # Should fail without weight
        with self.assertRaises(ValueError):
            HoldingDataDTO(ticker="AAPL", name="Apple Inc.", weight=None)

    def test_holding_data_dto_decimal_conversion(self):
        """Test automatic conversion to Decimal for weight fields."""
        dto = HoldingDataDTO(
            ticker="AAPL",
            name="Apple Inc.",
            weight=5.25,  # float
            shares=1000,  # int
            market_value=175000.00,  # float
        )

        self.assertIsInstance(dto.weight, Decimal)
        self.assertIsInstance(dto.shares, Decimal)
        self.assertIsInstance(dto.market_value, Decimal)

    def test_holding_data_dto_default_holding_type(self):
        """Test default holding_type value."""
        dto = HoldingDataDTO(ticker="AAPL", name="Apple Inc.", weight=Decimal("5.25"))

        self.assertEqual(dto.holding_type, "EQUITY")
