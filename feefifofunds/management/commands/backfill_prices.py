"""
Backfill historical asset price data from external sources.

Example usage:
    # Backfill last 30 days for AAPL from massive.com
    python manage.py backfill_prices --ticker AAPL --source massive --days 30

    # Backfill specific date range
    python manage.py backfill_prices --ticker AAPL --source finnhub --start 2024-01-01 --end 2024-12-31

    # Backfill all active assets
    python manage.py backfill_prices --source massive --days 365 --all

    # Backfill all assets using grouped endpoint (MUCH faster, fewer API calls!)
    python manage.py backfill_prices --source massive --days 365 --all --grouped
"""

from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from feefifofunds.models import Asset, AssetPrice
from feefifofunds.services.data_sources import DataSourceError, FinnhubDataSource, MassiveDataSource


class Command(BaseCommand):
    help = "Backfill historical asset price data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ticker",
            type=str,
            help="Asset ticker symbol (omit to backfill all active assets with --all)",
        )
        parser.add_argument(
            "--source",
            type=str,
            required=True,
            choices=["massive", "finnhub"],
            help="Data source name",
        )
        parser.add_argument(
            "--days",
            type=int,
            help="Number of days to backfill from today",
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
            "--all",
            action="store_true",
            help="Backfill all active assets",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created without saving to database",
        )
        parser.add_argument(
            "--grouped",
            action="store_true",
            help="Use grouped daily endpoint (1 API call per day instead of N calls). Only works with massive source and --all flag.",
        )

    def handle(self, *args, **options):
        source = options["source"].lower()
        dry_run = options["dry_run"]
        backfill_all = options["all"]
        use_grouped = options["grouped"]

        if use_grouped:
            if source != "massive":
                raise CommandError("--grouped only works with --source massive")
            if not backfill_all:
                raise CommandError("--grouped requires --all flag (use load_grouped_prices for single tickers)")
            return self._handle_grouped(options)

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

        if source == "massive" and requested_days > MassiveDataSource.max_free_tier_days:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Warning: Massive.com free tier limit is {MassiveDataSource.max_free_tier_days} days.\n"
                    f"   You requested {requested_days} days. You may get partial data or errors."
                )
            )
        elif source == "finnhub" and requested_days > FinnhubDataSource.max_free_tier_days:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Warning: Finnhub free tier estimated limit is {FinnhubDataSource.max_free_tier_days} days.\n"
                    f"   You requested {requested_days} days. You may get partial data or errors."
                )
            )

        if backfill_all:
            assets = Asset.objects.filter(active=True)
            if not assets.exists():
                raise CommandError("No active assets found")
            self.stdout.write(f"Backfilling {assets.count()} active assets...")
        else:
            if not options["ticker"]:
                raise CommandError("Must provide --ticker or use --all")
            ticker = options["ticker"].upper()
            try:
                assets = [Asset.objects.get(ticker=ticker)]
            except Asset.DoesNotExist:
                raise CommandError(f"Asset '{ticker}' not found")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be saved"))

        self.stdout.write(f"Date range: {start_date} to {end_date}\n")

        total_created = 0
        total_updated = 0
        failed_assets = []

        for asset in assets:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Processing: {asset.ticker} - {asset.name}")
            self.stdout.write(f"{'='*60}")

            try:
                price_data = self._fetch_price_data(asset.ticker, source, start_date, end_date)

                if not price_data:
                    self.stdout.write(self.style.WARNING(f"  No data found for {asset.ticker}"))
                    continue

                created, updated = self._save_prices(asset, price_data, source, dry_run)
                total_created += created
                total_updated += updated

                self.stdout.write(self.style.SUCCESS(f"  ✓ {asset.ticker}: Created {created}, updated {updated}"))

            except DataSourceError as e:
                self.stdout.write(self.style.ERROR(f"  ✗ {asset.ticker}: {str(e)}"))
                failed_assets.append((asset.ticker, str(e)))
                continue

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS("BACKFILL COMPLETE"))
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Total created: {total_created}")
        self.stdout.write(f"Total updated: {total_updated}")

        if failed_assets:
            self.stdout.write(f"\n{self.style.WARNING('Failed assets:')}")
            for ticker, error in failed_assets:
                self.stdout.write(f"  - {ticker}: {error}")

    def _handle_grouped(self, options):
        """Handle backfill using grouped daily endpoint."""
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

        assets = list(Asset.objects.filter(active=True))
        if not assets:
            raise CommandError("No active assets found")

        ticker_to_asset = {asset.ticker: asset for asset in assets}
        tickers_set = set(ticker_to_asset.keys())

        self.stdout.write(f"🚀 GROUPED MODE: Loading prices for {len(assets)} assets")
        self.stdout.write(f"Date range: {start_date} to {end_date}")
        self.stdout.write(
            self.style.SUCCESS(
                f"API calls needed: {requested_days} (vs {len(assets) * requested_days} without grouping)\n"
                f"Savings: {len(assets) * requested_days - requested_days} API calls!"
            )
        )

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

                created, updated = self._save_grouped_prices(matching_prices, ticker_to_asset, dry_run)
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
        self.stdout.write(self.style.SUCCESS("BACKFILL COMPLETE"))
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"API calls made: {total_api_calls}")
        self.stdout.write(f"Total created: {total_created}")
        self.stdout.write(f"Total updated: {total_updated}")

    @transaction.atomic
    def _save_grouped_prices(self, prices_by_ticker: dict, ticker_to_asset: dict, dry_run=False):
        """Save grouped price data to database."""
        created_count = 0
        updated_count = 0

        for ticker, price_data in prices_by_ticker.items():
            asset = ticker_to_asset.get(ticker)
            if not asset:
                continue

            if dry_run:
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

    def _fetch_price_data(self, ticker, source, start_date, end_date):
        """Fetch price data from the specified data source."""
        if source == "massive":
            data_source = MassiveDataSource()
        elif source == "finnhub":
            data_source = FinnhubDataSource()
        else:
            raise CommandError(f"Unknown data source: {source}")

        return data_source.fetch_historical_prices(ticker, start_date, end_date)

    @transaction.atomic
    def _save_prices(self, asset, price_data, source, dry_run=False):
        """Save price data to database."""
        created_count = 0
        updated_count = 0

        for data in price_data:
            if dry_run:
                created_count += 1
                continue

            price, created = AssetPrice.objects.update_or_create(
                asset=asset,
                timestamp=data["timestamp"],
                source=source,
                defaults={
                    "open": data["open"],
                    "high": data["high"],
                    "low": data["low"],
                    "close": data["close"],
                    "volume": data.get("volume"),
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        return created_count, updated_count
