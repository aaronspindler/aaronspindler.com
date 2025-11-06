"""
Ingest Kraken OHLCV (candle) data from CSV files.

Example usage:
    # Ingest daily data only
    python manage.py ingest_kraken_ohlcv --intervals 1440

    # Ingest hourly and daily data
    python manage.py ingest_kraken_ohlcv --intervals 60,1440

    # Ingest all intervals for a specific pair
    python manage.py ingest_kraken_ohlcv --pair BTCUSD

    # Dry run to preview what would be imported
    python manage.py ingest_kraken_ohlcv --intervals 1440 --dry-run

    # Skip files where asset already has data for this interval
    python manage.py ingest_kraken_ohlcv --intervals 1440 --skip-existing

    # Drop indexes before import, recreate after (faster for large imports)
    python manage.py ingest_kraken_ohlcv --intervals 1440 --drop-indexes
"""

import os
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from feefifofunds.models import Asset, AssetPrice
from feefifofunds.services.kraken import BulkInsertHelper, KrakenAssetCreator, KrakenPairParser, parse_ohlcv_csv
from utils.time import format_time


class Command(BaseCommand):
    help = "Ingest Kraken OHLCV (candle) data from CSV files"

    INTERVAL_MAP = {
        "1": 1,
        "5": 5,
        "15": 15,
        "30": 30,
        "60": 60,
        "240": 240,
        "720": 720,
        "1440": 1440,
        "Daily_OHLC": 1440,
        "Hourly_OHLC": 60,
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--intervals",
            type=str,
            default="1,5,15,30,60,240,720,1440",
            help="Comma-separated list of intervals to import (1,5,15,30,60,240,720,1440)",
        )
        parser.add_argument(
            "--pair",
            type=str,
            help="Import specific trading pair only (e.g., BTCUSD)",
        )
        parser.add_argument(
            "--directory",
            type=str,
            default="feefifofunds/data/kraken/Kraken_OHLCVT",
            help="Directory containing Kraken OHLCVT CSV files",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=25000,
            help="Number of records per batch (default: 25000)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be imported without saving to database",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip files for assets that already have data for this interval",
        )
        parser.add_argument(
            "--drop-indexes",
            action="store_true",
            help="Drop indexes before import and recreate after (faster for large imports)",
        )

    def handle(self, *args, **options):
        intervals_str = options["intervals"]
        pair_filter = options["pair"]
        data_dir = options["directory"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        skip_existing = options["skip_existing"]
        drop_indexes = options["drop_indexes"]

        intervals = [self.INTERVAL_MAP[i.strip()] for i in intervals_str.split(",")]

        if not os.path.exists(data_dir):
            self.stdout.write(self.style.ERROR(f"Directory not found: {data_dir}"))
            return

        csv_files = self._discover_files(data_dir, intervals, pair_filter)

        if not csv_files:
            self.stdout.write(self.style.WARNING("No CSV files found matching criteria"))
            return

        self.stdout.write(f"📂 Found {len(csv_files)} files to process")
        self.stdout.write(f"⚙️  Intervals: {', '.join(map(str, intervals))} minutes")
        self.stdout.write(f"📦 Batch size: {batch_size:,} records")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No data will be saved\n"))

        if drop_indexes and not dry_run:
            self.stdout.write("🗑️  Dropping indexes...")
            self._drop_indexes()

        asset_creator = KrakenAssetCreator()

        total_created = 0
        total_skipped = 0
        failed_files = []
        start_time = time.time()

        for index, (file_path, pair_name, interval) in enumerate(csv_files, start=1):
            elapsed = time.time() - start_time
            progress_pct = index / len(csv_files) * 100
            avg_time_per_file = elapsed / index
            remaining_files = len(csv_files) - index
            estimated_remaining = avg_time_per_file * remaining_files

            try:
                base_ticker, quote_currency = KrakenPairParser.parse_pair(pair_name)

                if skip_existing:
                    asset = Asset.objects.filter(ticker=base_ticker).first()
                    if (
                        asset
                        and AssetPrice.objects.filter(asset=asset, interval_minutes=interval, source="kraken").exists()
                    ):
                        total_skipped += 1
                        self.stdout.write(
                            f"⊘ [{index}/{len(csv_files)}] {pair_name:12} {interval:4}m - Skipped (exists) | "
                            f"{progress_pct:5.1f}% | ⏱️  {format_time(elapsed)} | ETA {format_time(estimated_remaining)}"
                        )
                        continue

                asset = asset_creator.get_or_create_asset(base_ticker, quote_currency)

                created = self._import_file(file_path, asset, interval, batch_size, dry_run)
                total_created += created

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ [{index}/{len(csv_files)}] {pair_name:12} {interval:4}m - +{created:6,} | "
                        f"{progress_pct:5.1f}% | ⏱️  {format_time(elapsed)} | ETA {format_time(estimated_remaining)}"
                    )
                )

            except Exception as e:
                failed_files.append((file_path, str(e)))
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ [{index}/{len(csv_files)}] {pair_name:12} {interval:4}m - {str(e)[:30]} | "
                        f"{progress_pct:5.1f}% | ⏱️  {format_time(elapsed)} | ETA {format_time(estimated_remaining)}"
                    )
                )

        if drop_indexes and not dry_run:
            self.stdout.write("\n🔧 Recreating indexes...")
            self._recreate_indexes()

        elapsed_total = time.time() - start_time
        success_count = len(csv_files) - len(failed_files) - total_skipped

        self.stdout.write(f"\n{'─' * 80}")
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

    def _discover_files(self, data_dir, intervals, pair_filter):
        csv_files = []
        for file_name in os.listdir(data_dir):
            if not file_name.endswith(".csv"):
                continue

            parts = file_name.rsplit("_", 1)
            if len(parts) != 2:
                continue

            pair_name = parts[0]
            interval_str = parts[1].replace(".csv", "")

            if interval_str not in self.INTERVAL_MAP:
                continue

            interval = self.INTERVAL_MAP[interval_str]

            if interval not in intervals:
                continue

            if pair_filter and pair_name.upper() != pair_filter.upper():
                continue

            file_path = os.path.join(data_dir, file_name)
            csv_files.append((file_path, pair_name, interval))

        csv_files.sort(key=lambda x: os.path.getsize(x[0]))

        return csv_files

    @transaction.atomic
    def _import_file(self, file_path, asset, interval, batch_size, dry_run):
        records_to_create = []
        created_count = 0

        for data in parse_ohlcv_csv(file_path, interval):
            created_count += 1

            if dry_run:
                continue

            records_to_create.append(
                AssetPrice(
                    asset=asset,
                    timestamp=data["timestamp"],
                    open=data["open"],
                    high=data["high"],
                    low=data["low"],
                    close=data["close"],
                    volume=data["volume"],
                    interval_minutes=data["interval_minutes"],
                    trade_count=data["trade_count"],
                    source="kraken",
                )
            )

            if len(records_to_create) >= batch_size:
                BulkInsertHelper.bulk_create_prices(records_to_create, batch_size)
                records_to_create = []

        if records_to_create and not dry_run:
            BulkInsertHelper.bulk_create_prices(records_to_create, batch_size)

        return created_count

    def _drop_indexes(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'feefifofunds_assetprice'
                AND indexname LIKE 'feefifofund_%_idx'
            """)
            indexes = [row[0] for row in cursor.fetchall()]

            for index_name in indexes:
                self.stdout.write(f"  Dropping {index_name}")
                cursor.execute(f"DROP INDEX IF EXISTS {index_name}")

    def _recreate_indexes(self):
        with connection.cursor() as cursor:
            self.stdout.write("  Creating index on (asset, timestamp, interval_minutes)...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS feefifofund_asset_i_b862eb_idx
                ON feefifofunds_assetprice (asset_id, timestamp, interval_minutes)
            """)

            self.stdout.write("  Creating index on (asset, interval_minutes)...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS feefifofund_asset_i_48d942_idx
                ON feefifofunds_assetprice (asset_id, interval_minutes)
            """)

            self.stdout.write("  Creating index on timestamp...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS feefifofund_timesta_ee2a80_idx
                ON feefifofunds_assetprice (timestamp)
            """)

            self.stdout.write("  Creating index on source...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS feefifofund_source_9e1b18_idx
                ON feefifofunds_assetprice (source)
            """)

            self.stdout.write("  Creating index on interval_minutes...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS feefifofund_interva_d09301_idx
                ON feefifofunds_assetprice (interval_minutes)
            """)
