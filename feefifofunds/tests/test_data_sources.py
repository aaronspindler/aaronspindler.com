"""
Tests for FeeFiFoFunds data source implementations.

These tests verify the functionality of data source classes including
the base class, DTOs, and specific data source implementations.
"""

from dataclasses import asdict
from datetime import date, datetime
from datetime import timezone as dt_timezone
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import requests
from django.test import TestCase, override_settings

from feefifofunds.services.data_sources.base import (
    BaseDataSource,
    DataNotFoundError,
    DataSourceError,
    RateLimitError,
)
from feefifofunds.services.data_sources.dto import PriceDataDTO
from feefifofunds.services.data_sources.finnhub import FinnhubDataSource
from feefifofunds.services.data_sources.kraken import KrakenDataSource
from feefifofunds.services.data_sources.massive import MassiveDataSource


class PriceDataDTOTest(TestCase):
    """Test cases for the PriceDataDTO class."""

    def test_dto_creation_with_all_fields(self):
        """Test creating a DTO with all fields."""
        test_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        dto = PriceDataDTO(
            ticker="BTC",
            timestamp=test_time,
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49000.00"),
            close=Decimal("50500.00"),
            volume=Decimal("1000000.00"),
            source="kraken",
        )

        actual_ticker = dto.ticker
        expected_ticker = "BTC"
        message = f"DTO ticker is {actual_ticker}, expected {expected_ticker}"
        self.assertEqual(actual_ticker, expected_ticker, message)

        actual_close = dto.close
        expected_close = Decimal("50500.00")
        message = f"DTO close price is {actual_close}, expected {expected_close}"
        self.assertEqual(actual_close, expected_close, message)

        actual_source = dto.source
        expected_source = "kraken"
        message = f"DTO source is {actual_source}, expected {expected_source}"
        self.assertEqual(actual_source, expected_source, message)

    def test_dto_creation_without_optional_fields(self):
        """Test creating a DTO without optional fields."""
        test_time = datetime.now(dt_timezone.utc)
        dto = PriceDataDTO(
            ticker="ETH",
            timestamp=test_time,
            open=Decimal("3000.00"),
            high=Decimal("3100.00"),
            low=Decimal("2900.00"),
            close=Decimal("3050.00"),
            # volume and source not provided
        )

        actual_volume = dto.volume
        expected_volume = None
        message = f"Optional volume is {actual_volume}, expected {expected_volume}"
        self.assertEqual(actual_volume, expected_volume, message)

        actual_source = dto.source
        expected_source = "unknown"
        message = f"Default source is {actual_source}, expected {expected_source}"
        self.assertEqual(actual_source, expected_source, message)

    def test_dto_validation_missing_ticker(self):
        """Test that missing ticker raises ValueError."""
        with self.assertRaises(ValueError) as context:
            PriceDataDTO(
                ticker="",  # Empty ticker
                timestamp=datetime.now(dt_timezone.utc),
                open=100,
                high=110,
                low=90,
                close=105,
            )

        actual_message = str(context.exception)
        expected_message = "Ticker is required"
        message = f"Error message is '{actual_message}', expected '{expected_message}'"
        self.assertEqual(actual_message, expected_message, message)

    def test_dto_validation_missing_timestamp(self):
        """Test that missing timestamp raises ValueError."""
        with self.assertRaises(ValueError) as context:
            PriceDataDTO(
                ticker="BTC",
                timestamp=None,  # Missing timestamp
                open=100,
                high=110,
                low=90,
                close=105,
            )

        actual_message = str(context.exception)
        expected_message = "Timestamp is required"
        message = f"Error message is '{actual_message}', expected '{expected_message}'"
        self.assertEqual(actual_message, expected_message, message)

    def test_dto_validation_missing_close_price(self):
        """Test that missing close price raises ValueError."""
        with self.assertRaises(ValueError) as context:
            PriceDataDTO(
                ticker="BTC",
                timestamp=datetime.now(dt_timezone.utc),
                open=100,
                high=110,
                low=90,
                close=None,  # Missing close
            )

        actual_message = str(context.exception)
        expected_message = "Close price is required"
        message = f"Error message is '{actual_message}', expected '{expected_message}'"
        self.assertEqual(actual_message, expected_message, message)

    def test_dto_decimal_conversion(self):
        """Test that numeric values are converted to Decimal."""
        dto = PriceDataDTO(
            ticker="BTC",
            timestamp=datetime.now(dt_timezone.utc),
            open=100,  # int
            high=110.5,  # float
            low="90.75",  # string
            close=Decimal("105.25"),  # already Decimal
            volume=1000000,
        )

        # All price fields should be Decimal
        self.assertIsInstance(dto.open, Decimal, "Open should be Decimal")
        self.assertIsInstance(dto.high, Decimal, "High should be Decimal")
        self.assertIsInstance(dto.low, Decimal, "Low should be Decimal")
        self.assertIsInstance(dto.close, Decimal, "Close should be Decimal")
        self.assertIsInstance(dto.volume, Decimal, "Volume should be Decimal")

    def test_dto_decimal_precision_rounding(self):
        """Test that excessive decimal precision is rounded."""
        dto = PriceDataDTO(
            ticker="BTC",
            timestamp=datetime.now(dt_timezone.utc),
            open=Decimal("100.123456789123456"),  # More than 8 decimal places
            high=110,
            low=90,
            close=105,
            volume=Decimal("1000000.123456789"),  # More than 2 decimal places for volume
        )

        # Should be rounded to 8 decimal places for prices
        actual_open = dto.open
        expected_open = Decimal("100.12345679")  # Rounded to 8 places
        message = f"Open price precision is {actual_open}, expected {expected_open}"
        self.assertEqual(actual_open, expected_open, message)

        # Volume should be rounded to 2 decimal places
        actual_volume = dto.volume
        expected_volume = Decimal("1000000.12")  # Rounded to 2 places
        message = f"Volume precision is {actual_volume}, expected {expected_volume}"
        self.assertEqual(actual_volume, expected_volume, message)

    def test_dto_as_dict(self):
        """Test converting DTO to dictionary."""
        test_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        dto = PriceDataDTO(
            ticker="BTC",
            timestamp=test_time,
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49000.00"),
            close=Decimal("50500.00"),
            volume=Decimal("1000000.00"),
            source="test",
        )

        dto_dict = asdict(dto)

        actual_keys = set(dto_dict.keys())
        expected_keys = {"ticker", "timestamp", "open", "high", "low", "close", "volume", "source"}
        message = f"Dictionary keys are {actual_keys}, expected {expected_keys}"
        self.assertEqual(actual_keys, expected_keys, message)

        actual_ticker = dto_dict["ticker"]
        expected_ticker = "BTC"
        message = f"Dict ticker is {actual_ticker}, expected {expected_ticker}"
        self.assertEqual(actual_ticker, expected_ticker, message)


class BaseDataSourceTest(TestCase):
    """Test cases for the BaseDataSource abstract class."""

    def test_base_class_is_abstract(self):
        """Test that BaseDataSource cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            BaseDataSource(api_key="test")  # pragma: allowlist secret

    def test_make_request_success(self):
        """Test successful request handling."""

        # Create a concrete implementation for testing
        class TestDataSource(BaseDataSource):
            name = "test"
            display_name = "Test Source"
            base_url = "https://api.test.com"

            def fetch_historical_prices(self, ticker, start_date, end_date):
                return []

        source = TestDataSource(api_key="test_key")

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}

        with patch.object(source.session, "get", return_value=mock_response):
            result = source._make_request("https://api.test.com/data")

            actual_result = result
            expected_result = {"data": "test"}
            message = f"Request result is {actual_result}, expected {expected_result}"
            self.assertEqual(actual_result, expected_result, message)

    def test_make_request_rate_limit_error(self):
        """Test that 429 status raises RateLimitError."""

        class TestDataSource(BaseDataSource):
            name = "test"
            display_name = "Test Source"
            base_url = "https://api.test.com"

            def fetch_historical_prices(self, ticker, start_date, end_date):
                return []

        source = TestDataSource()

        mock_response = Mock()
        mock_response.status_code = 429

        with patch.object(source.session, "get", return_value=mock_response):
            with self.assertRaises(RateLimitError) as context:
                source._make_request("https://api.test.com/data")

            actual_message = str(context.exception)
            expected_fragment = "Rate limit exceeded"
            message = f"Error message '{actual_message}' should contain '{expected_fragment}'"
            self.assertIn(expected_fragment, actual_message, message)

    def test_make_request_not_found_error(self):
        """Test that 404 status raises DataNotFoundError."""

        class TestDataSource(BaseDataSource):
            name = "test"
            display_name = "Test Source"
            base_url = "https://api.test.com"

            def fetch_historical_prices(self, ticker, start_date, end_date):
                return []

        source = TestDataSource()

        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(source.session, "get", return_value=mock_response):
            with self.assertRaises(DataNotFoundError) as context:
                source._make_request("https://api.test.com/data")

            actual_message = str(context.exception)
            expected_fragment = "Data not found"
            message = f"Error message '{actual_message}' should contain '{expected_fragment}'"
            self.assertIn(expected_fragment, actual_message, message)

    def test_make_request_retry_on_timeout(self):
        """Test that request retries on timeout."""

        class TestDataSource(BaseDataSource):
            name = "test"
            display_name = "Test Source"
            base_url = "https://api.test.com"

            def fetch_historical_prices(self, ticker, start_date, end_date):
                return []

        source = TestDataSource()

        # First two calls timeout, third succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "success"}

        with patch.object(
            source.session,
            "get",
            side_effect=[
                requests.exceptions.Timeout(),
                requests.exceptions.Timeout(),
                mock_response,
            ],
        ):
            result = source._make_request("https://api.test.com/data")

            actual_result = result
            expected_result = {"data": "success"}
            message = f"Result after retries is {actual_result}, expected {expected_result}"
            self.assertEqual(actual_result, expected_result, message)

    def test_make_request_max_retries_exceeded(self):
        """Test that max retries raises DataSourceError."""

        class TestDataSource(BaseDataSource):
            name = "test"
            display_name = "Test Source"
            base_url = "https://api.test.com"

            def fetch_historical_prices(self, ticker, start_date, end_date):
                return []

        source = TestDataSource()

        with patch.object(source.session, "get", side_effect=requests.exceptions.Timeout()):
            with self.assertRaises(DataSourceError) as context:
                source._make_request("https://api.test.com/data", max_retries=3)

            actual_message = str(context.exception)
            expected_fragment = "Request timeout after 3 attempts"
            message = f"Error message '{actual_message}' should contain '{expected_fragment}'"
            self.assertIn(expected_fragment, actual_message, message)


class FinnhubDataSourceTest(TestCase):
    """Test cases for the FinnhubDataSource class."""

    @override_settings(FINNHUB_API_KEY="test_api_key")  # pragma: allowlist secret
    def setUp(self):
        """Set up test data."""
        self.mock_client = MagicMock()
        self.patcher = patch("feefifofunds.services.data_sources.finnhub.finnhub.Client")
        mock_finnhub = self.patcher.start()
        mock_finnhub.return_value = self.mock_client

    def tearDown(self):
        """Clean up patches."""
        self.patcher.stop()

    def test_finnhub_initialization_with_api_key(self):
        """Test FinnhubDataSource initialization with API key."""
        source = FinnhubDataSource(api_key="custom_key")

        actual_key = source.api_key
        expected_key = "custom_key"
        message = f"API key is {actual_key}, expected {expected_key}"
        self.assertEqual(actual_key, expected_key, message)

        self.assertIsNotNone(source.client, "Finnhub client should be initialized")

    @override_settings(FINNHUB_API_KEY=None)
    def test_finnhub_initialization_without_api_key(self):
        """Test that missing API key raises error."""
        with self.assertRaises(DataSourceError) as context:
            FinnhubDataSource()

        actual_message = str(context.exception)
        expected_fragment = "FINNHUB_API_KEY is required"
        message = f"Error message '{actual_message}' should contain '{expected_fragment}'"
        self.assertIn(expected_fragment, actual_message, message)

    def test_fetch_historical_prices_success(self):
        """Test successful historical price fetch."""
        source = FinnhubDataSource(api_key="test_key")

        # Mock successful response
        mock_data = {
            "s": "ok",
            "t": [1609459200, 1609545600],  # Timestamps
            "o": [29000.00, 29250.00],  # Open prices
            "h": [29500.00, 30000.00],  # High prices
            "l": [28500.00, 29000.00],  # Low prices
            "c": [29250.00, 29750.00],  # Close prices
            "v": [1234567.89, 2345678.90],  # Volumes
        }
        self.mock_client.stock_candles.return_value = mock_data

        start = date(2021, 1, 1)
        end = date(2021, 1, 2)
        results = source.fetch_historical_prices("AAPL", start, end)

        actual_count = len(results)
        expected_count = 2
        message = f"Fetched {actual_count} price records, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

        # Check first result
        first_result = results[0]
        actual_close = first_result["close"]
        expected_close = Decimal("29250.00")
        message = f"First close price is {actual_close}, expected {expected_close}"
        self.assertEqual(actual_close, expected_close, message)

    def test_fetch_historical_prices_no_data(self):
        """Test handling of no data response."""
        source = FinnhubDataSource(api_key="test_key")

        self.mock_client.stock_candles.return_value = {"s": "no_data"}

        start = date(2021, 1, 1)
        end = date(2021, 1, 2)
        results = source.fetch_historical_prices("INVALID", start, end)

        actual_count = len(results)
        expected_count = 0
        message = f"No data should return {expected_count} results, got {actual_count}"
        self.assertEqual(actual_count, expected_count, message)

    def test_fetch_historical_prices_not_found(self):
        """Test handling of ticker not found."""
        source = FinnhubDataSource(api_key="test_key")

        self.mock_client.stock_candles.return_value = {"s": "error", "message": "Symbol not found"}

        with self.assertRaises(DataNotFoundError) as context:
            source.fetch_historical_prices("NOTFOUND", date(2021, 1, 1), date(2021, 1, 2))

        actual_message = str(context.exception)
        expected_fragment = "not found"
        message = f"Error message '{actual_message}' should contain '{expected_fragment}'"
        self.assertIn(expected_fragment, actual_message.lower(), message)

    def test_transform_results(self):
        """Test transformation of Finnhub data to standard format."""
        source = FinnhubDataSource(api_key="test_key")

        finnhub_data = {
            "t": [1609459200],
            "o": [100.50],
            "h": [105.00],
            "l": [99.00],
            "c": [103.25],
            "v": [1000000],
        }

        results = source._transform_results("AAPL", finnhub_data)

        actual_count = len(results)
        expected_count = 1
        message = f"Transformed {actual_count} records, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

        first_result = results[0]

        actual_ticker = first_result["ticker"]
        expected_ticker = "AAPL"
        message = f"Ticker is {actual_ticker}, expected {expected_ticker}"
        self.assertEqual(actual_ticker, expected_ticker, message)

        actual_timestamp = first_result["timestamp"]
        expected_timestamp = datetime.fromtimestamp(1609459200, tz=dt_timezone.utc)
        message = f"Timestamp is {actual_timestamp}, expected {expected_timestamp}"
        self.assertEqual(actual_timestamp, expected_timestamp, message)

        actual_close = first_result["close"]
        expected_close = Decimal("103.25")
        message = f"Close price is {actual_close}, expected {expected_close}"
        self.assertEqual(actual_close, expected_close, message)

        actual_source = first_result["source"]
        expected_source = "finnhub"
        message = f"Source is {actual_source}, expected {expected_source}"
        self.assertEqual(actual_source, expected_source, message)


class KrakenDataSourceTest(TestCase):
    """Test cases for the KrakenDataSource class."""

    def test_kraken_initialization(self):
        """Test KrakenDataSource initialization."""
        source = KrakenDataSource()

        actual_name = source.name
        expected_name = "kraken"
        message = f"Source name is {actual_name}, expected {expected_name}"
        self.assertEqual(actual_name, expected_name, message)

        actual_requires_key = source.requires_api_key
        expected_requires_key = False
        message = f"Requires API key is {actual_requires_key}, expected {expected_requires_key}"
        self.assertEqual(actual_requires_key, expected_requires_key, message)

    @patch("feefifofunds.services.data_sources.kraken.requests.get")
    def test_fetch_historical_prices_success(self, mock_get):
        """Test successful historical price fetch from Kraken."""
        source = KrakenDataSource()

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": [],
            "result": {
                "XXBTZUSD": [
                    [1609459200, "29000.00", "29500.00", "28500.00", "29250.00", "29250.00", "1234567.89", 1500],
                    [1609545600, "29250.00", "30000.00", "29000.00", "29750.00", "29750.00", "2345678.90", 2000],
                ]
            },
        }
        mock_get.return_value = mock_response

        start = date(2021, 1, 1)
        end = date(2021, 1, 2)
        results = source.fetch_historical_prices("XBTUSD", start, end)

        actual_count = len(results)
        expected_count = 2
        message = f"Fetched {actual_count} price records, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

    @patch("feefifofunds.services.data_sources.kraken.requests.get")
    def test_fetch_historical_prices_with_error(self, mock_get):
        """Test handling of Kraken API errors."""
        source = KrakenDataSource()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": ["Invalid pair"],
            "result": {},
        }
        mock_get.return_value = mock_response

        with self.assertRaises(DataSourceError) as context:
            source.fetch_historical_prices("INVALID", date(2021, 1, 1), date(2021, 1, 2))

        actual_message = str(context.exception)
        expected_fragment = "Invalid pair"
        message = f"Error message '{actual_message}' should contain '{expected_fragment}'"
        self.assertIn(expected_fragment, actual_message, message)


class MassiveDataSourceTest(TestCase):
    """Test cases for the MassiveDataSource class."""

    @override_settings(MASSIVE_API_KEY="test_api_key")  # pragma: allowlist secret
    def test_massive_initialization_with_api_key(self):
        """Test MassiveDataSource initialization with API key."""
        source = MassiveDataSource(api_key="custom_key")

        actual_key = source.api_key
        expected_key = "custom_key"
        message = f"API key is {actual_key}, expected {expected_key}"
        self.assertEqual(actual_key, expected_key, message)

    @override_settings(MASSIVE_API_KEY=None)
    def test_massive_initialization_without_api_key(self):
        """Test that missing API key raises error."""
        with self.assertRaises(DataSourceError) as context:
            MassiveDataSource()

        actual_message = str(context.exception)
        expected_fragment = "MASSIVE_API_KEY is required"
        message = f"Error message '{actual_message}' should contain '{expected_fragment}'"
        self.assertIn(expected_fragment, actual_message, message)

    @patch.object(MassiveDataSource, "_make_request")
    def test_fetch_historical_prices_success(self, mock_request):
        """Test successful historical price fetch from Massive."""
        source = MassiveDataSource(api_key="test_key")

        # Mock successful response
        mock_request.return_value = {
            "data": [
                {
                    "date": "2021-01-01",
                    "open": 29000.00,
                    "high": 29500.00,
                    "low": 28500.00,
                    "close": 29250.00,
                    "volume": 1234567.89,
                },
                {
                    "date": "2021-01-02",
                    "open": 29250.00,
                    "high": 30000.00,
                    "low": 29000.00,
                    "close": 29750.00,
                    "volume": 2345678.90,
                },
            ]
        }

        start = date(2021, 1, 1)
        end = date(2021, 1, 2)
        results = source.fetch_historical_prices("BTC", start, end)

        actual_count = len(results)
        expected_count = 2
        message = f"Fetched {actual_count} price records, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)


class DataSourceIntegrationTest(TestCase):
    """Integration tests for data source usage patterns."""

    def test_data_source_polymorphism(self):
        """Test that all data sources implement the same interface."""
        # Create mock data sources
        with patch("feefifofunds.services.data_sources.finnhub.finnhub.Client"):
            sources = [
                FinnhubDataSource(api_key="test"),  # pragma: allowlist secret
                KrakenDataSource(),
                MassiveDataSource(api_key="test"),  # pragma: allowlist secret
            ]

        for source in sources:
            # All should have required attributes
            self.assertTrue(hasattr(source, "name"), f"{source.__class__.__name__} should have 'name'")
            self.assertTrue(hasattr(source, "display_name"), f"{source.__class__.__name__} should have 'display_name'")
            self.assertTrue(
                hasattr(source, "requires_api_key"), f"{source.__class__.__name__} should have 'requires_api_key'"
            )

            # All should implement fetch_historical_prices
            self.assertTrue(
                hasattr(source, "fetch_historical_prices"),
                f"{source.__class__.__name__} should implement fetch_historical_prices",
            )

    def test_dto_creation_from_data_source_result(self):
        """Test creating DTOs from data source results."""
        # Simulate data source result
        source_result = {
            "ticker": "BTC",
            "timestamp": datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc),
            "open": Decimal("50000.00"),
            "high": Decimal("51000.00"),
            "low": Decimal("49000.00"),
            "close": Decimal("50500.00"),
            "volume": Decimal("1000000.00"),
            "source": "test",
        }

        # Create DTO from result
        dto = PriceDataDTO(**source_result)

        actual_ticker = dto.ticker
        expected_ticker = "BTC"
        message = f"DTO ticker from result is {actual_ticker}, expected {expected_ticker}"
        self.assertEqual(actual_ticker, expected_ticker, message)

        actual_close = dto.close
        expected_close = Decimal("50500.00")
        message = f"DTO close from result is {actual_close}, expected {expected_close}"
        self.assertEqual(actual_close, expected_close, message)
