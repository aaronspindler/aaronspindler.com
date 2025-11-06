"""
Ingest Kraken trade history (tick data) from CSV files.

Example usage:
    # Ingest all trading pairs
    python manage.py ingest_kraken_trades

    # Ingest specific trading pair
    python manage.py ingest_kraken_trades --pair BTCUSD

    # Dry run to preview what would be imported
    python manage.py ingest_kraken_trades --pair BTCUSD --dry-run

    # Skip files where asset already has trade data
    python manage.py ingest_kraken_trades --skip-existing

    # Drop indexes before import, recreate after (faster for large imports)
    python manage.py ingest_kraken_trades --drop-indexes

    # Limit records per file (useful for testing)
    python manage.py ingest_kraken_trades --pair BTCUSD --limit-per-file 10000

    # Skip confirmation prompt for automated runs
    python manage.py ingest_kraken_trades --yes
"""

import os
import shutil
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from feefifofunds.models import Asset, Trade
from feefifofunds.services.kraken import BulkInsertHelper, KrakenAssetCreator, KrakenPairParser, parse_trade_csv
from utils.time import format_time


class Command(BaseCommand):
    help = "Ingest Kraken trade history (tick data) from CSV files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pair",
            type=str,
            help="Import specific trading pair only (e.g., BTCUSD)",
        )
        parser.add_argument(
            "--directory",
            type=str,
            default="feefifofunds/data/kraken/Kraken_Trading_History",
            help="Directory containing Kraken Trading History CSV files",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50000,
            help="Number of records per batch (default: 50000)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be imported without saving to database",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip files for assets that already have trade data",
        )
        parser.add_argument(
            "--drop-indexes",
            action="store_true",
            help="Drop indexes before import and recreate after (faster for large imports)",
        )
        parser.add_argument(
            "--limit-per-file",
            type=int,
            help="Maximum number of records to import per file (for testing)",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt and proceed with ingestion",
        )

    def handle(self, *args, **options):
        pair_filter = options["pair"]
        data_dir = options["directory"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        skip_existing = options["skip_existing"]
        drop_indexes = options["drop_indexes"]
        limit_per_file = options["limit_per_file"]
        auto_approve = options["yes"]

        if not os.path.exists(data_dir):
            self.stdout.write(self.style.ERROR(f"Directory not found: {data_dir}"))
            return

        csv_files = self._discover_files(data_dir, pair_filter)

        if not csv_files:
            self.stdout.write(self.style.WARNING("No CSV files found matching criteria"))
            return

        self.stdout.write(f"📂 Found {len(csv_files)} files to process")
        self.stdout.write(f"📦 Batch size: {batch_size:,} records")

        if limit_per_file:
            self.stdout.write(f"⚠️  Limit: {limit_per_file:,} records per file")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No data will be saved"))

        self.stdout.write("\n📊 Counting lines in files...")
        self.stdout.write("📋 Files to be ingested:")
        self._display_file_list(csv_files)

        if not auto_approve:
            self.stdout.write(self.style.WARNING("\n⚠️  This will ingest the files listed above."))
            response = input("Continue with ingestion? [y/N]: ").strip().lower()
            if response not in ["y", "yes"]:
                self.stdout.write(self.style.WARNING("❌ Ingestion cancelled by user"))
                return

        self.stdout.write("")

        if drop_indexes and not dry_run:
            self.stdout.write("🗑️  Dropping indexes...")
            self._drop_indexes()

        asset_creator = KrakenAssetCreator()

        total_created = 0
        total_skipped = 0
        total_moved = 0
        failed_files = []
        start_time = time.time()

        ingested_dir = os.path.join(os.path.dirname(data_dir), "ingested", "Kraken_Trading_History")
        if not dry_run:
            os.makedirs(ingested_dir, exist_ok=True)

        for index, (file_path, pair_name) in enumerate(csv_files, start=1):
            elapsed = time.time() - start_time
            progress_pct = index / len(csv_files) * 100
            avg_time_per_file = elapsed / index
            remaining_files = len(csv_files) - index
            estimated_remaining = avg_time_per_file * remaining_files

            try:
                line_count = self._count_file_lines(file_path)
                base_ticker, quote_currency = KrakenPairParser.parse_pair(pair_name)

                if skip_existing:
                    asset = Asset.objects.filter(ticker=base_ticker).first()
                    if asset and Trade.objects.filter(asset=asset, source="kraken").exists():
                        total_skipped += 1
                        self.stdout.write(
                            f"⊘ [{index}/{len(csv_files)}] {pair_name:12} - Skipped (exists) | "
                            f"{line_count:>10,} lines | {progress_pct:5.1f}% | ⏱️  {format_time(elapsed)} | ETA {format_time(estimated_remaining)}"
                        )
                        continue

                asset = asset_creator.get_or_create_asset(base_ticker, quote_currency)

                created = self._import_file(file_path, asset, batch_size, dry_run, limit_per_file)
                total_created += created

                if not dry_run:
                    dest_path = os.path.join(ingested_dir, os.path.basename(file_path))
                    shutil.move(file_path, dest_path)
                    total_moved += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ [{index}/{len(csv_files)}] {pair_name:12} - +{created:8,} | "
                        f"{line_count:>10,} lines | {progress_pct:5.1f}% | ⏱️  {format_time(elapsed)} | ETA {format_time(estimated_remaining)}"
                    )
                )

            except Exception as e:
                failed_files.append((file_path, str(e)))
                try:
                    line_count = self._count_file_lines(file_path)
                    line_info = f"{line_count:>10,} lines | "
                except Exception:
                    line_info = ""
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ [{index}/{len(csv_files)}] {pair_name:12} - {str(e)[:30]} | "
                        f"{line_info}{progress_pct:5.1f}% | ⏱️  {format_time(elapsed)} | ETA {format_time(estimated_remaining)}"
                    )
                )

        if drop_indexes and not dry_run:
            self.stdout.write("\n🔧 Recreating indexes...")
            self._recreate_indexes()

        elapsed_total = time.time() - start_time
        success_count = len(csv_files) - len(failed_files) - total_skipped

        self.stdout.write(f"\n{'─' * 80}")
        if not dry_run and total_moved > 0:
            self.stdout.write(f"📁 Moved {total_moved} file(s) to {ingested_dir}")
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Complete: {success_count}/{len(csv_files)} files | "
                f"+{total_created:,} records created | "
                f"⊘ {total_skipped} skipped | "
                f"⏱️  {format_time(elapsed_total)}"
            )
        )

        if failed_files:
            self.stdout.write(self.style.WARNING(f"\n⚠️  {len(failed_files)} files failed:"))
            for file_path, error in failed_files[:10]:
                self.stdout.write(f"  • {Path(file_path).name}: {error[:60]}")

    def _display_file_list(self, csv_files):
        total_files = len(csv_files)
        for idx, (file_path, pair_name) in enumerate(csv_files, start=1):
            self.stdout.write(f"  [{idx}/{total_files}] Counting {pair_name}...", ending="\r")
            self.stdout.flush()
            line_count = self._count_file_lines(file_path)
            self.stdout.write(f"  • {pair_name:12} → {line_count:>10,} lines{' ' * 20}\n", ending="")
            self.stdout.flush()

    def _count_file_lines(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) - 1

    def _discover_files(self, data_dir, pair_filter):
        csv_files = []
        for file_name in os.listdir(data_dir):
            if not file_name.endswith(".csv"):
                continue

            pair_name = file_name.replace(".csv", "")

            if pair_filter and pair_name.upper() != pair_filter.upper():
                continue

            file_path = os.path.join(data_dir, file_name)
            csv_files.append((file_path, pair_name))

        csv_files.sort(key=lambda x: os.path.getsize(x[0]))

        return csv_files

    @transaction.atomic
    def _import_file(self, file_path, asset, batch_size, dry_run, limit_per_file):
        records_to_create = []
        created_count = 0
        processed_count = 0

        for data in parse_trade_csv(file_path):
            if limit_per_file and processed_count >= limit_per_file:
                break

            processed_count += 1

            if dry_run:
                created_count += 1
                continue

            records_to_create.append(
                Trade(
                    asset=asset,
                    timestamp=data["timestamp"],
                    price=data["price"],
                    volume=data["volume"],
                    source="kraken",
                )
            )

            if len(records_to_create) >= batch_size:
                BulkInsertHelper.bulk_create_trades(records_to_create, batch_size)
                created_count += len(records_to_create)
                records_to_create = []

        if records_to_create and not dry_run:
            BulkInsertHelper.bulk_create_trades(records_to_create, batch_size)
            created_count += len(records_to_create)

        return created_count

    def _drop_indexes(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'feefifofunds_trade'
                AND indexname LIKE 'feefifofund_%_idx'
            """)
            indexes = [row[0] for row in cursor.fetchall()]

            for index_name in indexes:
                self.stdout.write(f"  Dropping {index_name}")
                cursor.execute(f"DROP INDEX IF EXISTS {index_name}")

    def _recreate_indexes(self):
        with connection.cursor() as cursor:
            self.stdout.write("  Creating index on (asset, timestamp)...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS feefifofund_asset_i_542a46_idx
                ON feefifofunds_trade (asset_id, timestamp)
            """)

            self.stdout.write("  Creating index on timestamp...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS feefifofund_timesta_6dc787_idx
                ON feefifofunds_trade (timestamp)
            """)

            self.stdout.write("  Creating index on asset...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS feefifofund_asset_i_b2d2eb_idx
                ON feefifofunds_trade (asset_id)
            """)

            self.stdout.write("  Creating index on source...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS feefifofund_source_1e2f3a_idx
                ON feefifofunds_trade (source)
            """)
