"""
Management command to fetch fund data from external sources.

Usage:
    python manage.py fetch_fund VFV.TO
    python manage.py fetch_fund VFV.TO VGRO.TO XIC.TO
    python manage.py fetch_fund --file tickers.txt
    python manage.py fetch_fund VFV.TO --source yahoo --dry-run
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from feefifofunds.data_sources import AlphaVantageSource, DataSourceManager, YahooFinanceSource

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch fund data from external sources (Yahoo Finance, Alpha Vantage)"

    def add_arguments(self, parser):
        parser.add_argument("tickers", nargs="*", type=str, help="Fund tickers to fetch (e.g., VFV.TO, VOO)")

        parser.add_argument(
            "--file", type=str, help="File containing tickers (one per line)", dest="ticker_file", default=None
        )

        parser.add_argument(
            "--source",
            type=str,
            choices=["yahoo", "alpha_vantage", "all"],
            default="all",
            help="Data source to use (default: all, with fallback)",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch data but don't save to database",
        )

        parser.add_argument(
            "--update-existing",
            action="store_true",
            default=True,
            help="Update existing funds (default: True)",
        )

        parser.add_argument(
            "--alpha-vantage-key",
            type=str,
            help="Alpha Vantage API key (or set ALPHA_VANTAGE_API_KEY env var)",
            default=None,
        )

    def handle(self, *args, **options):
        # Get tickers from args or file
        tickers = options["tickers"]
        ticker_file = options["ticker_file"]

        if ticker_file:
            try:
                with open(ticker_file) as f:
                    file_tickers = [line.strip() for line in f if line.strip()]
                tickers.extend(file_tickers)
            except FileNotFoundError:
                raise CommandError(f"Ticker file not found: {ticker_file}")

        if not tickers:
            raise CommandError("No tickers provided. Use positional args or --file")

        # Remove duplicates
        tickers = list(dict.fromkeys(tickers))

        self.stdout.write(f"Fetching {len(tickers)} fund(s): {', '.join(tickers)}")

        # Setup data source manager
        manager = DataSourceManager()

        source_choice = options["source"]
        if source_choice in ["yahoo", "all"]:
            try:
                manager.add_source(YahooFinanceSource())
                self.stdout.write(self.style.SUCCESS("✓ Added Yahoo Finance source"))
            except ImportError as e:
                self.stdout.write(self.style.WARNING(f"⚠ Yahoo Finance unavailable: {e}"))

        if source_choice in ["alpha_vantage", "all"]:
            api_key = options.get("alpha_vantage_key")
            try:
                manager.add_source(AlphaVantageSource(api_key=api_key))
                self.stdout.write(self.style.SUCCESS("✓ Added Alpha Vantage source"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠ Alpha Vantage unavailable: {e}"))

        if not manager.sources:
            raise CommandError("No data sources available. Check dependencies and API keys.")

        # Fetch funds
        dry_run = options["dry_run"]
        update_existing = options["update_existing"]

        success_count = 0
        skip_count = 0
        error_count = 0

        for ticker in tickers:
            try:
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"Fetching: {ticker}")
                self.stdout.write(f"{'='*60}")

                # Fetch data
                fund_data = manager.fetch_fund(ticker)

                if not fund_data:
                    self.stdout.write(self.style.ERROR(f"✗ No data found for {ticker}"))
                    skip_count += 1
                    continue

                # Display fetched data
                self._display_fund_data(fund_data)

                if dry_run:
                    self.stdout.write(self.style.WARNING(f"⚠ DRY RUN: Would save {ticker} to database"))
                    success_count += 1
                    continue

                # Save to database
                fund = manager.save_to_db(fund_data, update_existing=update_existing)

                if fund:
                    self.stdout.write(self.style.SUCCESS(f"✓ Saved {ticker} to database (ID: {fund.id})"))
                    success_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"⚠ Skipped {ticker} (already exists)"))
                    skip_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error processing {ticker}: {e}"))
                logger.exception(f"Error fetching {ticker}")
                error_count += 1
                continue

        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS("SUMMARY"))
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Total tickers: {len(tickers)}")
        self.stdout.write(self.style.SUCCESS(f"✓ Success: {success_count}"))
        self.stdout.write(self.style.WARNING(f"⚠ Skipped: {skip_count}"))
        self.stdout.write(self.style.ERROR(f"✗ Errors: {error_count}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠ DRY RUN MODE: No changes were saved to database"))

    def _display_fund_data(self, fund_data):
        """Display fund data in a readable format."""
        self.stdout.write("\nFund Data:")
        self.stdout.write(f"  Ticker: {fund_data.ticker}")
        self.stdout.write(f"  Name: {fund_data.name}")
        self.stdout.write(f"  Provider: {fund_data.provider_name}")
        self.stdout.write(f"  Type: {fund_data.fund_type}")

        if fund_data.mer:
            self.stdout.write(f"  MER: {fund_data.mer}%")

        if fund_data.asset_class:
            self.stdout.write(f"  Asset Class: {fund_data.asset_class}")

        if fund_data.geographic_focus:
            self.stdout.write(f"  Geographic Focus: {fund_data.geographic_focus}")

        if fund_data.one_year_return:
            self.stdout.write(f"  1-Year Return: {fund_data.one_year_return}%")

        if fund_data.aum:
            self.stdout.write(f"  AUM: ${fund_data.aum}M")

        self.stdout.write(f"  Source: {fund_data.source_name}")
        self.stdout.write(f"  Complete: {fund_data.is_complete()}")
