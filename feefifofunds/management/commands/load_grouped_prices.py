"""
Load asset prices using Polygon's grouped daily endpoint (batch mode).

This is MUCH more efficient than load_prices when fetching data for multiple tickers.
Instead of N API calls (one per ticker), this makes 1 API call per day.

Example usage:
    # Load prices for all active stocks for 7 days (only 7 API calls!)
    python manage.py load_grouped_prices --days 7

    # Load specific date range
    python manage.py load_grouped_prices --start 2024-01-01 --end 2024-01-31

    # Filter by category
    python manage.py load_grouped_prices --days 30 --category STOCK

    # Dry-run to preview
    python manage.py load_grouped_prices --days 7 --dry-run
"""

from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from feefifofunds.models import Asset, AssetPrice
from feefifofunds.services.data_sources import DataSourceError, MassiveDataSource


class Command(BaseCommand):
    help = "Load asset prices using grouped daily endpoint (1 API call per day)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            help="Number of days to load from today",
        )
        parser.add_argument(
            "--start",
            type=str,
            help="Start date (YYYY-MM-DD format)",
        )
        parser.add_argument(
            "--end",
            type=str,
            help="End date (YYYY-MM-DD format, defaults to today)",
        )
        parser.add_argument(
            "--category",
            type=str,
            choices=["STOCK", "CRYPTO", "COMMODITY", "CURRENCY"],
            help="Only load prices for specific asset category",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created without saving to database",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if options["days"]:
            end_date = date.today()
            start_date = end_date - timedelta(days=options["days"])
            requested_days = options["days"]
        elif options["start"]:
            start_date = datetime.strptime(options["start"], "%Y-%m-%d").date()
            end_date = datetime.strptime(options["end"], "%Y-%m-%d").date() if options["end"] else date.today()
            requested_days = (end_date - start_date).days
        else:
            raise CommandError("Must provide either --days or --start")

        if requested_days > MassiveDataSource.max_free_tier_days:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Warning: Massive.com free tier limit is {MassiveDataSource.max_free_tier_days} days.\n"
                    f"   You requested {requested_days} days. You may get partial data or errors."
                )
            )

        asset_filter = {"active": True}
        if options["category"]:
            asset_filter["category"] = options["category"]

        assets = list(Asset.objects.filter(**asset_filter))
        if not assets:
            raise CommandError("No active assets found")

        ticker_to_asset = {asset.ticker: asset for asset in assets}
        tickers_set = set(ticker_to_asset.keys())

        self.stdout.write(f"Loading prices for {len(assets)} assets")
        if options["category"]:
            self.stdout.write(f"Category filter: {options['category']}")
        self.stdout.write(f"Date range: {start_date} to {end_date}")
        self.stdout.write(f"API calls needed: {requested_days} (vs {len(assets) * requested_days} without grouping)")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be saved\n"))

        try:
            data_source = MassiveDataSource()
        except DataSourceError as e:
            raise CommandError(f"Failed to initialize data source: {str(e)}")

        total_created = 0
        total_updated = 0
        total_api_calls = 0
        current_date = start_date

        while current_date <= end_date:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Fetching: {current_date}")
            self.stdout.write(f"{'='*60}")

            try:
                all_prices = data_source.fetch_grouped_daily(current_date)
                total_api_calls += 1

                matching_prices = {ticker: data for ticker, data in all_prices.items() if ticker in tickers_set}

                if not matching_prices:
                    self.stdout.write(self.style.WARNING(f"  No data found for our assets on {current_date}"))
                    current_date += timedelta(days=1)
                    continue

                created, updated = self._save_prices(matching_prices, ticker_to_asset, dry_run)
                total_created += created
                total_updated += updated

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ {current_date}: {len(matching_prices)} tickers, " f"created {created}, updated {updated}"
                    )
                )

            except DataSourceError as e:
                self.stdout.write(self.style.ERROR(f"  ✗ {current_date}: {str(e)}"))

            current_date += timedelta(days=1)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS("LOAD COMPLETE"))
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"API calls made: {total_api_calls}")
        self.stdout.write(f"Total created: {total_created}")
        self.stdout.write(f"Total updated: {total_updated}")
        self.stdout.write(
            f"\nEfficiency: Saved {(len(assets) * requested_days) - total_api_calls} API calls "
            f"vs loading tickers individually!"
        )

    @transaction.atomic
    def _save_prices(self, prices_by_ticker: dict, ticker_to_asset: dict, dry_run=False):
        """Save price data to database."""
        created_count = 0
        updated_count = 0

        for ticker, price_data in prices_by_ticker.items():
            asset = ticker_to_asset.get(ticker)
            if not asset:
                continue

            if dry_run:
                self.stdout.write(
                    f"    Would save: {ticker} - "
                    f"O:{price_data['open']} H:{price_data['high']} "
                    f"L:{price_data['low']} C:{price_data['close']}"
                )
                created_count += 1
                continue

            price, created = AssetPrice.objects.update_or_create(
                asset=asset,
                timestamp=price_data["timestamp"],
                source="massive",
                defaults={
                    "open": price_data["open"],
                    "high": price_data["high"],
                    "low": price_data["low"],
                    "close": price_data["close"],
                    "volume": price_data.get("volume"),
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        return created_count, updated_count
