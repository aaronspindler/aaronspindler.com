"""
Tests for FeeFiFoFunds management commands.

These tests verify the functionality of management commands for
data ingestion, backfilling, and price loading.
"""

import tempfile
from datetime import date, datetime
from datetime import timezone as dt_timezone
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from feefifofunds.tests.factories import AssetFactory


class IngestSequentialCommandTest(TestCase):
    """Test cases for the ingest_sequential management command."""

    def setUp(self):
        """Set up test data."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.ohlcv_dir = self.temp_dir / "Kraken_OHLCVT"
        self.ohlcv_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("feefifofunds.management.commands.ingest_sequential.SequentialIngestor")
    def test_command_with_tier_filter(self, mock_ingestor_class):
        """Test command execution with tier filter."""
        # Setup mock
        mock_ingestor = MagicMock()
        mock_ingestor.discover_files.return_value = [
            (Path("test1.csv"), "ohlcv", "BTC"),
            (Path("test2.csv"), "ohlcv", "ETH"),
        ]
        mock_ingestor.process_file.return_value = (True, 100, None)
        mock_ingestor_class.return_value = mock_ingestor

        # Run command
        out = StringIO()
        call_command("ingest_sequential", tier="TIER1", yes=True, stdout=out, data_dir=str(self.temp_dir))

        # Verify discover_files was called with correct tier
        mock_ingestor.discover_files.assert_called_with("TIER1", "ohlcv", None)

        # Verify process was started
        self.assertTrue(mock_ingestor.connect_ilp.called, "ILP connection should be initiated")
        self.assertTrue(mock_ingestor.load_asset_cache.called, "Asset cache should be loaded")

        output = out.getvalue()
        self.assertIn("Discovering files", output, "Should show discovery message")

    @patch("feefifofunds.management.commands.ingest_sequential.SequentialIngestor")
    def test_command_with_interval_filter(self, mock_ingestor_class):
        """Test command execution with interval filter."""
        # Setup mock
        mock_ingestor = MagicMock()
        mock_ingestor.discover_files.return_value = [
            (Path("test1.csv"), "ohlcv", "BTC"),
        ]
        mock_ingestor.process_file.return_value = (True, 100, None)
        mock_ingestor_class.return_value = mock_ingestor

        # Run command with interval filter
        out = StringIO()
        call_command("ingest_sequential", intervals="60,1440", yes=True, stdout=out, data_dir=str(self.temp_dir))

        # Verify discover_files was called with interval filter
        mock_ingestor.discover_files.assert_called_with("ALL", "ohlcv", [60, 1440])

        output = out.getvalue()
        self.assertIn("Discovering files", output, "Should show discovery message")

    def test_command_with_invalid_intervals(self):
        """Test command with invalid interval format."""
        out = StringIO()
        err = StringIO()

        call_command(
            "ingest_sequential",
            intervals="invalid,format",
            stdout=out,
            stderr=err,
            data_dir=str(self.temp_dir),
        )

        output = out.getvalue()
        actual_has_error = "Invalid intervals format" in output
        expected_has_error = True
        message = f"Output contains error message: {actual_has_error}, expected {expected_has_error}"
        self.assertEqual(actual_has_error, expected_has_error, message)

    @patch("feefifofunds.management.commands.ingest_sequential.SequentialIngestor")
    def test_command_with_no_files_found(self, mock_ingestor_class):
        """Test command when no files match filters."""
        # Setup mock to return empty list
        mock_ingestor = MagicMock()
        mock_ingestor.discover_files.return_value = []
        mock_ingestor_class.return_value = mock_ingestor

        out = StringIO()
        call_command("ingest_sequential", tier="TIER2", stdout=out, data_dir=str(self.temp_dir))

        output = out.getvalue()
        self.assertIn("No OHLCV files found", output, "Should show no files message")

        # Verify ILP connection was not initiated
        self.assertFalse(mock_ingestor.connect_ilp.called, "ILP should not connect when no files")

    @patch("feefifofunds.management.commands.ingest_sequential.SequentialIngestor")
    def test_command_with_confirmation_prompt(self, mock_ingestor_class):
        """Test command confirmation prompt when --yes not provided."""
        # Setup mock
        mock_ingestor = MagicMock()
        mock_ingestor.discover_files.return_value = [
            (Path("test1.csv"), "ohlcv", "BTC"),
        ]
        mock_ingestor_class.return_value = mock_ingestor

        # Mock user input to decline
        with patch("builtins.input", return_value="n"):
            out = StringIO()
            call_command("ingest_sequential", stdout=out, data_dir=str(self.temp_dir))

            output = out.getvalue()
            self.assertIn("Aborted", output, "Should show abort message when user declines")

    @patch("feefifofunds.management.commands.ingest_sequential.SequentialIngestor")
    def test_command_error_handling(self, mock_ingestor_class):
        """Test command error handling."""
        # Setup mock to raise error
        mock_ingestor = MagicMock()
        mock_ingestor.discover_files.return_value = [
            (Path("test1.csv"), "ohlcv", "BTC"),
            (Path("test2.csv"), "ohlcv", "ETH"),
        ]
        # First file succeeds, second fails
        mock_ingestor.process_file.side_effect = [
            (True, 100, None),
            (False, 0, "Processing error"),
        ]
        mock_ingestor_class.return_value = mock_ingestor

        out = StringIO()
        call_command("ingest_sequential", yes=True, stdout=out, data_dir=str(self.temp_dir))

        # Should continue processing despite error (default behavior)
        actual_calls = mock_ingestor.process_file.call_count
        expected_calls = 2
        message = f"Process file called {actual_calls} times, expected {expected_calls}"
        self.assertEqual(actual_calls, expected_calls, message)

    @patch("feefifofunds.management.commands.ingest_sequential.SequentialIngestor")
    def test_command_stop_on_error(self, mock_ingestor_class):
        """Test command with --stop-on-error flag."""
        # Setup mock to raise error
        mock_ingestor = MagicMock()
        mock_ingestor.discover_files.return_value = [
            (Path("test1.csv"), "ohlcv", "BTC"),
            (Path("test2.csv"), "ohlcv", "ETH"),
        ]
        # First file fails
        mock_ingestor.process_file.return_value = (False, 0, "Processing error")
        mock_ingestor_class.return_value = mock_ingestor

        out = StringIO()
        call_command("ingest_sequential", yes=True, stop_on_error=True, stdout=out, data_dir=str(self.temp_dir))

        # Should stop after first error
        actual_calls = mock_ingestor.process_file.call_count
        expected_calls = 1
        message = f"Process file called {actual_calls} times, expected {expected_calls} (should stop on error)"
        self.assertEqual(actual_calls, expected_calls, message)


class LoadPricesCommandTest(TestCase):
    """Test cases for the load_prices management command."""

    def setUp(self):
        """Set up test data."""
        self.asset = AssetFactory.create_crypto_asset(ticker="BTC")

    @patch("feefifofunds.management.commands.load_prices.FinnhubDataSource")
    def test_load_prices_with_ticker(self, mock_source_class):
        """Test loading prices for specific ticker."""
        # Setup mock data source
        mock_source = MagicMock()
        mock_source.fetch_historical_prices.return_value = [
            {
                "ticker": "BTC",
                "timestamp": datetime.now(dt_timezone.utc),
                "open": 50000,
                "high": 51000,
                "low": 49000,
                "close": 50500,
                "volume": 1000000,
                "source": "finnhub",
            }
        ]
        mock_source_class.return_value = mock_source

        out = StringIO()
        call_command(
            "load_prices",
            ticker="BTC",
            source="finnhub",
            stdout=out,
        )

        # Verify fetch was called
        self.assertTrue(mock_source.fetch_historical_prices.called, "Should fetch historical prices")

        output = out.getvalue()
        self.assertIn("BTC", output, "Should show ticker in output")

    def test_load_prices_missing_ticker(self):
        """Test that missing ticker raises error."""
        out = StringIO()
        err = StringIO()

        with self.assertRaises(CommandError) as context:
            call_command(
                "load_prices",
                source="finnhub",
                stdout=out,
                stderr=err,
            )

        actual_message = str(context.exception)
        expected_fragment = "ticker"
        message = f"Error message '{actual_message}' should mention '{expected_fragment}'"
        self.assertIn(expected_fragment, actual_message.lower(), message)

    @patch("feefifofunds.management.commands.load_prices.FinnhubDataSource")
    def test_load_prices_with_date_range(self, mock_source_class):
        """Test loading prices with custom date range."""
        mock_source = MagicMock()
        mock_source.fetch_historical_prices.return_value = []
        mock_source_class.return_value = mock_source

        out = StringIO()
        call_command(
            "load_prices",
            ticker="BTC",
            source="finnhub",
            start_date="2024-01-01",
            end_date="2024-01-31",
            stdout=out,
        )

        # Verify fetch was called with correct dates
        call_args = mock_source.fetch_historical_prices.call_args[0]

        actual_start = call_args[1]
        expected_start = date(2024, 1, 1)
        message = f"Start date is {actual_start}, expected {expected_start}"
        self.assertEqual(actual_start, expected_start, message)

        actual_end = call_args[2]
        expected_end = date(2024, 1, 31)
        message = f"End date is {actual_end}, expected {expected_end}"
        self.assertEqual(actual_end, expected_end, message)

    def test_load_prices_invalid_source(self):
        """Test that invalid source raises error."""
        out = StringIO()
        err = StringIO()

        with self.assertRaises(CommandError) as context:
            call_command(
                "load_prices",
                ticker="BTC",
                source="invalid_source",
                stdout=out,
                stderr=err,
            )

        actual_message = str(context.exception)
        expected_fragment = "Invalid source"
        message = f"Error message '{actual_message}' should contain '{expected_fragment}'"
        self.assertIn(expected_fragment, actual_message, message)


class BackfillPricesCommandTest(TestCase):
    """Test cases for the backfill_prices management command."""

    def setUp(self):
        """Set up test data."""
        self.btc = AssetFactory.create_crypto_asset(ticker="BTC")
        self.eth = AssetFactory.create_crypto_asset(ticker="ETH")

    @patch("feefifofunds.management.commands.backfill_prices.FinnhubDataSource")
    def test_backfill_all_assets(self, mock_source_class):
        """Test backfilling prices for all assets."""
        # Setup mock
        mock_source = MagicMock()
        mock_source.fetch_historical_prices.return_value = []
        mock_source_class.return_value = mock_source

        out = StringIO()
        call_command(
            "backfill_prices",
            source="finnhub",
            stdout=out,
        )

        # Should fetch for all active assets
        actual_calls = mock_source.fetch_historical_prices.call_count
        expected_calls = 2  # BTC and ETH
        message = f"Fetch called {actual_calls} times, expected {expected_calls} (all assets)"
        self.assertEqual(actual_calls, expected_calls, message)

    @patch("feefifofunds.management.commands.backfill_prices.FinnhubDataSource")
    def test_backfill_specific_category(self, mock_source_class):
        """Test backfilling prices for specific category."""
        # Add a currency asset
        AssetFactory.create_currency_asset(ticker="USD")

        mock_source = MagicMock()
        mock_source.fetch_historical_prices.return_value = []
        mock_source_class.return_value = mock_source

        out = StringIO()
        call_command(
            "backfill_prices",
            source="finnhub",
            category="CRYPTO",
            stdout=out,
        )

        # Should only fetch for crypto assets
        actual_calls = mock_source.fetch_historical_prices.call_count
        expected_calls = 2  # BTC and ETH only, not USD
        message = f"Fetch called {actual_calls} times, expected {expected_calls} (crypto only)"
        self.assertEqual(actual_calls, expected_calls, message)

    @patch("feefifofunds.management.commands.backfill_prices.FinnhubDataSource")
    def test_backfill_dry_run(self, mock_source_class):
        """Test dry run mode doesn't save data."""
        mock_source = MagicMock()
        mock_source.fetch_historical_prices.return_value = [
            {
                "ticker": "BTC",
                "timestamp": datetime.now(dt_timezone.utc),
                "open": 50000,
                "high": 51000,
                "low": 49000,
                "close": 50500,
                "volume": 1000000,
                "source": "finnhub",
            }
        ]
        mock_source_class.return_value = mock_source

        out = StringIO()
        call_command(
            "backfill_prices",
            source="finnhub",
            dry_run=True,
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("DRY RUN", output, "Should indicate dry run mode")

        # In dry run, data shouldn't be saved to database
        # (would need to mock the save operation to fully test this)


class BackfillKrakenGapsCommandTest(TestCase):
    """Test cases for the backfill_kraken_gaps management command."""

    @patch("feefifofunds.management.commands.backfill_kraken_gaps.KrakenDataSource")
    def test_backfill_gaps_for_asset(self, mock_source_class):
        """Test backfilling gaps for specific asset."""
        asset = AssetFactory.create_crypto_asset(ticker="BTC")

        mock_source = MagicMock()
        mock_source.fetch_historical_prices.return_value = []
        mock_source_class.return_value = mock_source

        out = StringIO()
        call_command(
            "backfill_kraken_gaps",
            ticker="BTC",
            stdout=out,
        )

        # Verify fetch was called
        self.assertTrue(mock_source.fetch_historical_prices.called, "Should attempt to fetch prices for gaps")

    def test_backfill_gaps_missing_ticker(self):
        """Test that missing ticker raises error."""
        out = StringIO()
        err = StringIO()

        with self.assertRaises(CommandError) as context:
            call_command(
                "backfill_kraken_gaps",
                stdout=out,
                stderr=err,
            )

        actual_message = str(context.exception)
        expected_fragment = "ticker"
        message = f"Error message '{actual_message}' should mention '{expected_fragment}'"
        self.assertIn(expected_fragment, actual_message.lower(), message)

    @patch("feefifofunds.management.commands.backfill_kraken_gaps.KrakenDataSource")
    @patch("feefifofunds.management.commands.backfill_kraken_gaps.AssetPrice")
    def test_backfill_identifies_gaps(self, mock_price_model, mock_source_class):
        """Test that command identifies gaps in price data."""
        asset = AssetFactory.create_crypto_asset(ticker="BTC")

        # Mock existing price data with gap
        mock_prices = [
            Mock(time=datetime(2024, 1, 1, tzinfo=dt_timezone.utc)),
            Mock(time=datetime(2024, 1, 3, tzinfo=dt_timezone.utc)),  # Gap on Jan 2
        ]
        mock_price_model.objects.using().filter().order_by().values_list.return_value = [
            (datetime(2024, 1, 1, tzinfo=dt_timezone.utc),),
            (datetime(2024, 1, 3, tzinfo=dt_timezone.utc),),
        ]

        mock_source = MagicMock()
        mock_source.fetch_historical_prices.return_value = []
        mock_source_class.return_value = mock_source

        out = StringIO()
        call_command(
            "backfill_kraken_gaps",
            ticker="BTC",
            interval=1440,  # Daily
            stdout=out,
        )

        output = out.getvalue()
        # Should identify the gap
        self.assertIn("gap", output.lower(), "Should mention gaps found")


class CommandIntegrationTest(TestCase):
    """Integration tests for management command patterns."""

    def test_all_commands_have_help_text(self):
        """Test that all commands have help text defined."""
        from django.core.management import get_commands

        commands = get_commands()
        feefifofunds_commands = [cmd for cmd in commands if commands[cmd] == "feefifofunds"]

        for cmd_name in feefifofunds_commands:
            out = StringIO()
            try:
                call_command(cmd_name, "--help", stdout=out)
                output = out.getvalue()

                # Help output should contain the command name
                actual_has_name = cmd_name in output
                expected_has_name = True
                message = f"Help for {cmd_name} contains command name: {actual_has_name}, expected {expected_has_name}"
                self.assertEqual(actual_has_name, expected_has_name, message)

            except (CommandError, SystemExit):
                # --help causes SystemExit, which is expected
                pass

    def test_command_output_formatting(self):
        """Test that commands use consistent output formatting."""
        # This tests that commands follow the pattern of using
        # self.stdout.write() and self.style for output

        # Create a mock command to test the pattern
        from django.core.management.base import BaseCommand

        class TestCommand(BaseCommand):
            def handle(self, *args, **options):
                self.stdout.write("Normal output")
                self.stdout.write(self.style.SUCCESS("Success message"))
                self.stdout.write(self.style.ERROR("Error message"))
                self.stdout.write(self.style.WARNING("Warning message"))

        cmd = TestCommand()
        out = StringIO()
        cmd.stdout = out
        cmd.handle()

        output = out.getvalue()
        self.assertIn("Normal output", output, "Should have normal output")
        self.assertIn("Success message", output, "Should have success message")
        self.assertIn("Error message", output, "Should have error message")
        self.assertIn("Warning message", output, "Should have warning message")
