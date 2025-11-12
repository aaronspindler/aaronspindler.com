"""
Management command to initialize QuestDB schema for time-series tables.

Creates the assetprice table in QuestDB with optimized schema
including SYMBOL types, PARTITION BY DAY, and designated timestamps.
"""

from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = "Initialize QuestDB schema for AssetPrice table"

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            type=str,
            default="questdb",
            help="Database to use (default: questdb)",
        )
        parser.add_argument(
            "--drop",
            action="store_true",
            help="Drop existing tables before creating (DANGEROUS)",
        )

    def handle(self, *args, **options):
        database = options["database"]
        drop_tables = options["drop"]

        self.stdout.write("\n📊 QuestDB Schema Setup")
        self.stdout.write("─" * 60)

        try:
            with connections[database].cursor() as cursor:
                # Drop tables if requested
                if drop_tables:
                    self.stdout.write(self.style.WARNING("\n⚠️  Dropping existing table..."))
                    cursor.execute("DROP TABLE IF EXISTS assetprice")
                    self.stdout.write(self.style.SUCCESS("✓ Table dropped"))

                # Create AssetPrice table
                self.stdout.write("\n📈 Creating assetprice table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS assetprice (
                        asset_id INT,
                        time TIMESTAMP,
                        open DOUBLE,
                        high DOUBLE,
                        low DOUBLE,
                        close DOUBLE,
                        volume DOUBLE,
                        interval_minutes INT,
                        trade_count INT,
                        quote_currency SYMBOL CAPACITY 256 CACHE,
                        source SYMBOL CAPACITY 256 CACHE
                    ) timestamp(time) PARTITION BY DAY;
                """)
                self.stdout.write(self.style.SUCCESS("✓ assetprice table created"))

                # Verify table
                self.stdout.write("\n🔍 Verifying table...")
                cursor.execute("""
                    SELECT table_name
                    FROM tables()
                    WHERE table_name = 'assetprice'
                """)
                tables = [row[0] for row in cursor.fetchall()]

                if len(tables) == 1:
                    self.stdout.write(self.style.SUCCESS(f"✓ Found table: {tables[0]}"))
                else:
                    self.stdout.write(self.style.WARNING("⚠️  assetprice table not found"))

            self.stdout.write("\n" + "─" * 60)
            self.stdout.write(self.style.SUCCESS("\n✅ QuestDB schema initialization complete!"))
            self.stdout.write("\nNext steps:")
            self.stdout.write("  1. Run migrations for Asset model: python manage.py migrate")
            self.stdout.write(
                "  2. Start ingesting data: python manage.py ingest_sequential --tier TIER1 --intervals 1440"
            )
            self.stdout.write()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error: {str(e)}"))
            self.stdout.write("\nTroubleshooting:")
            self.stdout.write("  • Ensure QUESTDB_URL is set in your .env file")
            self.stdout.write("  • Format: postgresql://admin:password@srv-captain--questdb:8812/qdb")
            self.stdout.write("  • Verify QuestDB is running and accessible")
            raise
