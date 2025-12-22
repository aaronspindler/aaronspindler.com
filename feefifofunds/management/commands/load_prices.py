from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from feefifofunds.models import Asset, AssetPrice
from feefifofunds.services.data_sources import DataSourceError, FinnhubDataSource, MassiveDataSource


class Command(BaseCommand):
    help = "Load asset price data into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ticker",
            type=str,
            required=True,
            help="Asset ticker symbol (e.g., AAPL, MSFT for stocks)",
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
            default=7,
            help="Number of days to fetch (default: 7)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created without saving to database",
        )

    def handle(self, *args, **options):
        ticker = options["ticker"].upper()
        source = options["source"].lower()
        days = options["days"]
        dry_run = options["dry_run"]

        try:
            asset = Asset.objects.get(ticker=ticker)
        except Asset.DoesNotExist as e:
            raise CommandError(
                f"Asset '{ticker}' not found. Create it first via Django admin or create_asset command."
            ) from e

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        if source == "massive" and days > MassiveDataSource.max_free_tier_days:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Warning: Massive.com free tier limit is {MassiveDataSource.max_free_tier_days} days.\n"
                    f"   You requested {days} days. You may get partial data or errors."
                )
            )
        elif source == "finnhub" and days > FinnhubDataSource.max_free_tier_days:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Warning: Finnhub free tier estimated limit is {FinnhubDataSource.max_free_tier_days} days.\n"
                    f"   You requested {days} days. You may get partial data or errors."
                )
            )

        self.stdout.write(
            f"Loading prices for {asset.name} ({ticker}) from {source}...\nDate range: {start_date} to {end_date}"
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be saved"))

        try:
            price_data = self._fetch_price_data(ticker, source, start_date, end_date)
        except DataSourceError as e:
            raise CommandError(f"Failed to fetch data: {str(e)}") from e

        if not price_data:
            self.stdout.write(self.style.WARNING(f"No price data found for {ticker} from {source}"))
            return

        created_count, updated_count = self._save_prices(asset, price_data, source, dry_run)

        self.stdout.write(self.style.SUCCESS(f"✓ Created {created_count} prices, updated {updated_count} prices"))

    def _fetch_price_data(self, ticker, source, start_date, end_date):
        if source == "massive":
            data_source = MassiveDataSource()
        elif source == "finnhub":
            data_source = FinnhubDataSource()
        else:
            raise CommandError(f"Unknown data source: {source}")

        self.stdout.write(f"Fetching data from {data_source.display_name}...")
        return data_source.fetch_historical_prices(ticker, start_date, end_date)

    @transaction.atomic
    def _save_prices(self, asset, price_data, source, dry_run=False):
        created_count = 0
        updated_count = 0

        for data in price_data:
            if dry_run:
                self.stdout.write(
                    f"  Would create: {data['timestamp']} - "
                    f"O:{data['open']} H:{data['high']} L:{data['low']} C:{data['close']}"
                )
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
                self.stdout.write(f"  ✓ Created: {price.timestamp} - Close: ${price.close}")
            else:
                updated_count += 1
                self.stdout.write(f"  ↻ Updated: {price.timestamp} - Close: ${price.close}")

        return created_count, updated_count
