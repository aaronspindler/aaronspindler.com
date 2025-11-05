"""
Populate the database with popular ETFs and stocks, then backfill their price data.

Example usage:
    # Create and backfill top 10 assets with 1 year of data
    python manage.py populate_popular_assets --source massive --days 365 --limit 10

    # Create and backfill all popular assets with 30 days of data
    python manage.py populate_popular_assets --source finnhub --days 30

    # Just create assets without backfilling (dry run for backfill)
    python manage.py populate_popular_assets --create-only

    # Create specific category
    python manage.py populate_popular_assets --source massive --days 365 --category etfs
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from feefifofunds.models import Asset, AssetPrice
from feefifofunds.services.data_sources import DataSourceError, FinnhubDataSource, MassiveDataSource

POPULAR_ASSETS = {
    "etfs": [
        ("SPY", "SPDR S&P 500 ETF Trust", "Tracks S&P 500 index"),
        ("QQQ", "Invesco QQQ Trust", "Tracks Nasdaq-100 index"),
        ("IWM", "iShares Russell 2000 ETF", "Tracks Russell 2000 small-cap index"),
        ("VTI", "Vanguard Total Stock Market ETF", "Total US stock market"),
        ("VOO", "Vanguard S&P 500 ETF", "Tracks S&P 500 index"),
        ("VEA", "Vanguard FTSE Developed Markets ETF", "International developed markets"),
        ("VWO", "Vanguard FTSE Emerging Markets ETF", "Emerging markets"),
        ("AGG", "iShares Core U.S. Aggregate Bond ETF", "US investment-grade bonds"),
        ("BND", "Vanguard Total Bond Market ETF", "Total US bond market"),
        ("GLD", "SPDR Gold Shares", "Physical gold"),
        ("VNQ", "Vanguard Real Estate ETF", "US real estate investment trusts"),
        ("XLF", "Financial Select Sector SPDR Fund", "US financial sector"),
        ("XLE", "Energy Select Sector SPDR Fund", "US energy sector"),
        ("XLK", "Technology Select Sector SPDR Fund", "US technology sector"),
        ("XLV", "Health Care Select Sector SPDR Fund", "US healthcare sector"),
        ("ARKK", "ARK Innovation ETF", "Disruptive innovation"),
        ("TLT", "iShares 20+ Year Treasury Bond ETF", "Long-term US Treasury bonds"),
        ("EEM", "iShares MSCI Emerging Markets ETF", "Emerging markets equity"),
        ("DIA", "SPDR Dow Jones Industrial Average ETF", "Tracks Dow Jones"),
        ("IEMG", "iShares Core MSCI Emerging Markets ETF", "Emerging markets core"),
    ],
    "mega_cap_stocks": [
        ("AAPL", "Apple Inc.", "Consumer electronics and software"),
        ("MSFT", "Microsoft Corporation", "Software and cloud computing"),
        ("GOOGL", "Alphabet Inc. Class A", "Internet services and advertising"),
        ("AMZN", "Amazon.com Inc.", "E-commerce and cloud computing"),
        ("NVDA", "NVIDIA Corporation", "Graphics processing units and AI chips"),
        ("META", "Meta Platforms Inc.", "Social media and metaverse"),
        ("TSLA", "Tesla Inc.", "Electric vehicles and clean energy"),
        ("BRK.B", "Berkshire Hathaway Inc. Class B", "Diversified holding company"),
        ("V", "Visa Inc.", "Payment processing"),
        ("JPM", "JPMorgan Chase & Co.", "Banking and financial services"),
        ("WMT", "Walmart Inc.", "Retail corporation"),
        ("MA", "Mastercard Incorporated", "Payment processing"),
        ("UNH", "UnitedHealth Group Inc.", "Healthcare and insurance"),
        ("JNJ", "Johnson & Johnson", "Pharmaceuticals and consumer health"),
        ("XOM", "Exxon Mobil Corporation", "Oil and gas"),
    ],
    "growth_stocks": [
        ("NFLX", "Netflix Inc.", "Streaming entertainment"),
        ("DIS", "The Walt Disney Company", "Entertainment and media"),
        ("AMD", "Advanced Micro Devices Inc.", "Semiconductors"),
        ("ADBE", "Adobe Inc.", "Creative software"),
        ("CRM", "Salesforce Inc.", "Cloud-based CRM software"),
        ("ORCL", "Oracle Corporation", "Database software and cloud"),
        ("INTC", "Intel Corporation", "Semiconductors"),
        ("CSCO", "Cisco Systems Inc.", "Networking equipment"),
        ("PYPL", "PayPal Holdings Inc.", "Online payments"),
        ("ABNB", "Airbnb Inc.", "Short-term rental platform"),
    ],
}


class Command(BaseCommand):
    help = "Populate database with popular ETFs and stocks, then backfill price data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            choices=["massive", "finnhub"],
            help="Data source for price backfill",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Number of days of historical data to backfill (default: 365)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of assets to process (useful for testing)",
        )
        parser.add_argument(
            "--category",
            type=str,
            choices=["etfs", "mega_cap_stocks", "growth_stocks", "all"],
            default="all",
            help="Which category of assets to populate (default: all)",
        )
        parser.add_argument(
            "--create-only",
            action="store_true",
            help="Only create assets without backfilling price data",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip assets that already exist",
        )

    def handle(self, *args, **options):
        source = options.get("source")
        days = options["days"]
        limit = options.get("limit")
        category = options["category"]
        create_only = options["create_only"]
        skip_existing = options["skip_existing"]

        if not create_only and not source:
            raise self.style.ERROR("Must provide --source unless using --create-only")

        self.stdout.write("=" * 60)
        self.stdout.write("POPULATING POPULAR ASSETS")
        self.stdout.write("=" * 60)

        assets_to_process = self._get_assets_list(category, limit)

        self.stdout.write(f"Processing {len(assets_to_process)} assets from category: {category}")
        if limit:
            self.stdout.write(f"Limited to first {limit} assets")

        created_assets = []
        skipped_assets = []
        failed_creates = []

        for ticker, name, description in assets_to_process:
            try:
                asset, created = self._create_asset(ticker, name, description, skip_existing)
                if created:
                    created_assets.append(asset)
                    self.stdout.write(self.style.SUCCESS(f"✓ Created: {ticker} - {name}"))
                else:
                    skipped_assets.append(ticker)
                    self.stdout.write(f"  Exists: {ticker}")
            except Exception as e:
                failed_creates.append((ticker, str(e)))
                self.stdout.write(self.style.ERROR(f"✗ Failed to create {ticker}: {str(e)}"))

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("ASSET CREATION SUMMARY")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Created: {len(created_assets)}")
        self.stdout.write(f"Already existed: {len(skipped_assets)}")
        if failed_creates:
            self.stdout.write(self.style.ERROR(f"Failed: {len(failed_creates)}"))

        if create_only:
            self.stdout.write("\n--create-only flag set, skipping price backfill")
            return

        if source == "massive" and days > MassiveDataSource.max_free_tier_days:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  Warning: Massive.com free tier limit is {MassiveDataSource.max_free_tier_days} days.\n"
                    f"   You requested {days} days. You may get partial data or errors.\n"
                )
            )
        elif source == "finnhub" and days > FinnhubDataSource.max_free_tier_days:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  Warning: Finnhub free tier estimated limit is {FinnhubDataSource.max_free_tier_days} days.\n"
                    f"   You requested {days} days. You may get partial data or errors.\n"
                )
            )

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"BACKFILLING PRICE DATA FROM {source.upper()}")
        self.stdout.write(f"Date range: Last {days} days")
        self.stdout.write(f"{'='*60}\n")

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        all_assets_to_backfill = []
        if created_assets:
            all_assets_to_backfill.extend(created_assets)
        if not skip_existing and skipped_assets:
            all_assets_to_backfill.extend(Asset.objects.filter(ticker__in=skipped_assets))

        total_created = 0
        total_updated = 0
        failed_backfills = []

        for asset in all_assets_to_backfill:
            self.stdout.write(f"\n{'─'*60}")
            self.stdout.write(f"Processing: {asset.ticker} - {asset.name}")
            self.stdout.write(f"{'─'*60}")

            try:
                price_data = self._fetch_price_data(asset.ticker, source, start_date, end_date)

                if not price_data:
                    self.stdout.write(self.style.WARNING(f"  No data found for {asset.ticker}"))
                    continue

                created, updated = self._save_prices(asset, price_data, source)
                total_created += created
                total_updated += updated

                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ {asset.ticker}: Created {created}, updated {updated} prices")
                )

            except DataSourceError as e:
                self.stdout.write(self.style.ERROR(f"  ✗ {asset.ticker}: {str(e)}"))
                failed_backfills.append((asset.ticker, str(e)))
                continue

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS("BACKFILL COMPLETE"))
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Total price records created: {total_created}")
        self.stdout.write(f"Total price records updated: {total_updated}")

        if failed_backfills:
            self.stdout.write(f"\n{self.style.WARNING('Failed backfills:')}")
            for ticker, error in failed_backfills:
                self.stdout.write(f"  - {ticker}: {error}")

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS("ALL DONE! 🎉"))
        self.stdout.write(f"{'='*60}")

    def _get_assets_list(self, category, limit):
        """Get list of assets to process based on category and limit."""
        if category == "all":
            assets = []
            for cat_assets in POPULAR_ASSETS.values():
                assets.extend(cat_assets)
        else:
            assets = POPULAR_ASSETS[category]

        if limit:
            assets = assets[:limit]

        return assets

    @transaction.atomic
    def _create_asset(self, ticker, name, description, skip_existing):
        """Create an asset if it doesn't exist."""
        if skip_existing:
            asset = Asset.objects.filter(ticker=ticker).first()
            if asset:
                return asset, False

        asset, created = Asset.objects.get_or_create(
            ticker=ticker,
            defaults={
                "name": name,
                "category": "STOCK",
                "quote_currency": "USD",
                "description": description,
                "active": True,
            },
        )
        return asset, created

    def _fetch_price_data(self, ticker, source, start_date, end_date):
        """Fetch price data from the specified data source."""
        if source == "massive":
            data_source = MassiveDataSource()
        elif source == "finnhub":
            data_source = FinnhubDataSource()
        else:
            raise DataSourceError(f"Unknown data source: {source}")

        return data_source.fetch_historical_prices(ticker, start_date, end_date)

    @transaction.atomic
    def _save_prices(self, asset, price_data, source):
        """Save price data to database."""
        created_count = 0
        updated_count = 0

        for data in price_data:
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
