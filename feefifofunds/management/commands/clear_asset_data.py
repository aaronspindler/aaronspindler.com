"""
Management command to clear all data from Asset, AssetPrice, and Trade tables.

Usage:
    python manage.py clear_asset_data                  # Will prompt for confirmation
    python manage.py clear_asset_data --yes           # Skip confirmation
    python manage.py clear_asset_data --tables prices # Clear only prices and trades
    python manage.py clear_asset_data --dry-run       # Preview what would be deleted
"""

from django.core.management.base import BaseCommand

from feefifofunds.models import Asset, AssetPrice, Trade


class Command(BaseCommand):
    help = "Clear all data from Asset, AssetPrice, and Trade tables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt",
        )
        parser.add_argument(
            "--tables",
            type=str,
            choices=["all", "prices", "assets"],
            default="all",
            help="Which tables to clear (default: all)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--database",
            type=str,
            default="questdb",
            help="Database to use (default: questdb for prices/trades, default for assets)",
        )

    def handle(self, *args, **options):
        auto_approve = options["yes"]
        tables = options["tables"]
        dry_run = options["dry_run"]
        database = options["database"]

        # Count existing data
        asset_count = Asset.objects.using(database).count()
        price_count = AssetPrice.objects.using(database).count()
        trade_count = Trade.objects.using(database).count()

        self.stdout.write(f"\n📊 Current data in {database} database:")
        self.stdout.write(f"   Assets:       {asset_count:,}")
        self.stdout.write(f"   Asset Prices: {price_count:,}")
        self.stdout.write(f"   Trades:       {trade_count:,}")

        if asset_count == 0 and price_count == 0 and trade_count == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ Tables are already empty!"))
            return

        # Determine what will be deleted
        tables_to_clear = []
        if tables in ["all", "prices"]:
            if price_count > 0:
                tables_to_clear.append(("AssetPrice", price_count))
            if trade_count > 0:
                tables_to_clear.append(("Trade", trade_count))
        if tables in ["all", "assets"]:
            if asset_count > 0:
                tables_to_clear.append(("Asset", asset_count))

        if not tables_to_clear:
            self.stdout.write(self.style.WARNING("\n⚠️  No data to clear based on selected tables"))
            return

        # Display what will be deleted
        self.stdout.write(self.style.WARNING("\n🗑️  Will delete:"))
        total_records = 0
        for table_name, count in tables_to_clear:
            self.stdout.write(f"   {table_name:12} {count:,} records")
            total_records += count

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\n🔍 DRY RUN: Would delete {total_records:,} records"))
            return

        # Confirm deletion
        if not auto_approve:
            self.stdout.write(
                self.style.ERROR(f"\n⚠️  WARNING: This will permanently delete {total_records:,} records!")
            )
            response = input("Are you sure you want to continue? [y/N]: ").strip().lower()
            if response not in ["y", "yes"]:
                self.stdout.write(self.style.WARNING("❌ Cancelled by user"))
                return

        self.stdout.write("")

        # Perform deletion
        deleted_counts = {}

        try:
            # Clear prices first (due to foreign key constraints)
            if tables in ["all", "prices"]:
                if price_count > 0:
                    self.stdout.write("🔄 Clearing AssetPrice table...")
                    deleted_prices = AssetPrice.objects.using(database).all().delete()
                    deleted_counts["AssetPrice"] = deleted_prices[0]
                    self.stdout.write(f"   ✓ Deleted {deleted_counts['AssetPrice']:,} price records")

                if trade_count > 0:
                    self.stdout.write("🔄 Clearing Trade table...")
                    deleted_trades = Trade.objects.using(database).all().delete()
                    deleted_counts["Trade"] = deleted_trades[0]
                    self.stdout.write(f"   ✓ Deleted {deleted_counts['Trade']:,} trade records")

            # Clear assets
            if tables in ["all", "assets"]:
                if asset_count > 0:
                    self.stdout.write("🔄 Clearing Asset table...")
                    deleted_assets = Asset.objects.using(database).all().delete()
                    deleted_counts["Asset"] = deleted_assets[0]
                    self.stdout.write(f"   ✓ Deleted {deleted_counts['Asset']:,} asset records")

            # Summary
            total_deleted = sum(deleted_counts.values())
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Successfully cleared {total_deleted:,} records from {len(deleted_counts)} table(s)"
                )
            )

            # Suggest vacuum for large deletions
            if database == "questdb" and total_deleted > 100000:
                self.stdout.write(
                    self.style.WARNING(
                        "\n💡 Tip: QuestDB automatically manages disk space.\n" "   No manual vacuum required."
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error during deletion: {str(e)}"))
            raise
