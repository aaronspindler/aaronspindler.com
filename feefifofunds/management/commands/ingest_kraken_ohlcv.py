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

    # Skip confirmation prompt for automated runs
    python manage.py ingest_kraken_ohlcv --intervals 1440 --yes

    # Update existing records instead of skipping duplicates
    python manage.py ingest_kraken_ohlcv --intervals 1440 --update-existing

    # Re-ingest files to update data (safe, won't create duplicates)
    python manage.py ingest_kraken_ohlcv --intervals 1440 --update-existing --yes
"""

import io
import os
import shutil
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone

from feefifofunds.models import Asset, AssetPrice
from feefifofunds.services.kraken import KrakenAssetCreator, KrakenPairParser, parse_ohlcv_csv
from utils.time import format_time


class Command(BaseCommand):
    help = """Ingest Kraken OHLCV (candle) data from CSV files.

    Features:
    - Uses PostgreSQL COPY with staging table for optimal performance (50k-100k records/sec)
    - Supports upsert/update mode for re-ingestion (--update-existing)
    - Handles duplicates gracefully with ON CONFLICT DO NOTHING/UPDATE
    - Optimized skip-existing check with single query
    - Progress tracking with ETAs
    - Automatic file moving to ingested/ directory after success
    - TimescaleDB hypertable support with automatic chunk management
    """

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
            help="Skip files for assets that already have data for this interval",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt and proceed with ingestion",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update existing records instead of skipping duplicates",
        )
        parser.add_argument(
            "--database",
            type=str,
            default="timescaledb",
            help="Database to use (default: timescaledb)",
        )
        parser.add_argument(
            "--tier",
            type=str,
            choices=["TIER1", "TIER2", "TIER3", "TIER4", "UNCLASSIFIED", "auto"],
            help="Tier to assign to new assets (TIER1-4, UNCLASSIFIED, or 'auto' to determine based on ticker)",
        )
        parser.add_argument(
            "--only-tier",
            type=str,
            action="append",
            choices=["TIER1", "TIER2", "TIER3", "TIER4", "UNCLASSIFIED"],
            help="Only ingest assets matching specified tier(s). Can be used multiple times.",
        )

    def handle(self, *args, **options):
        intervals_str = options["intervals"]
        pair_filter = options["pair"]
        data_dir = options["directory"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        skip_existing = options["skip_existing"]
        auto_approve = options["yes"]
        update_existing = options["update_existing"]
        database = options["database"]
        tier_option = options["tier"]
        only_tiers = options["only_tier"]

        intervals = [self.INTERVAL_MAP[i.strip()] for i in intervals_str.split(",")]

        if not os.path.exists(data_dir):
            self.stdout.write(self.style.ERROR(f"Directory not found: {data_dir}"))
            return

        csv_files = self._discover_files(data_dir, intervals, pair_filter)

        if not csv_files:
            self.stdout.write(self.style.WARNING("No CSV files found matching criteria"))
            return

        # Filter files based on --only-tier if specified
        if only_tiers:
            csv_files = self._filter_by_tier(csv_files, only_tiers)
            if not csv_files:
                self.stdout.write(self.style.WARNING(f"No CSV files found for tiers: {', '.join(only_tiers)}"))
                return

        self.stdout.write(f"📂 Found {len(csv_files)} files to process")
        self.stdout.write(f"⚙️  Intervals: {', '.join(map(str, intervals))} minutes")
        self.stdout.write(f"📦 Batch size: {batch_size:,} records")

        if tier_option:
            tier_msg = "auto-determine based on ticker" if tier_option == "auto" else tier_option
            self.stdout.write(f"🏷️  Tier assignment: {tier_msg}")

        if only_tiers:
            self.stdout.write(f"🔍 Filtering for tiers: {', '.join(only_tiers)}")

        if update_existing:
            self.stdout.write(self.style.SUCCESS("🔄 UPDATE MODE - Existing records will be updated"))
        else:
            self.stdout.write("⊘ SKIP MODE - Existing records will be skipped (default)")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No data will be saved"))

        self.stdout.write("\n📊 Counting lines and caching results...")
        line_count_cache = self._cache_line_counts(csv_files)

        self.stdout.write("📋 Files to be ingested:")
        self._display_file_list(csv_files, line_count_cache)

        if not auto_approve:
            self.stdout.write(self.style.WARNING("\n⚠️  This will ingest the files listed above."))
            response = input("Continue with ingestion? [y/N]: ").strip().lower()
            if response not in ["y", "yes"]:
                self.stdout.write(self.style.WARNING("❌ Ingestion cancelled by user"))
                return

        self.stdout.write("")

        # Determine default tier for asset creator
        default_tier = None if tier_option == "auto" else tier_option
        asset_creator = KrakenAssetCreator(database=database, default_tier=default_tier)

        if not dry_run:
            self.stdout.write("🏗️  Pre-creating assets...")
            unique_pairs = {pair_name for _, pair_name, _ in csv_files}
            # Pass tier if not auto mode
            bulk_tier = None if tier_option == "auto" else tier_option
            asset_creator.bulk_create_assets(list(unique_pairs), tier=bulk_tier)
            self.stdout.write(f"✓ Pre-created {len(unique_pairs)} assets")

        if skip_existing:
            self.stdout.write("🔍 Building skip-existing index...")
            skip_set = self._build_skip_set(csv_files, database)
            self.stdout.write(f"✓ Found {len(skip_set)} existing asset-interval combinations to skip")

        total_created = 0
        total_skipped = 0
        total_moved = 0
        failed_files = []
        start_time = time.time()

        ingested_dir = os.path.join(os.path.dirname(data_dir), "ingested", "Kraken_OHLCVT")
        if not dry_run:
            os.makedirs(ingested_dir, exist_ok=True)

        for index, (file_path, pair_name, interval) in enumerate(csv_files, start=1):
            elapsed = time.time() - start_time
            progress_pct = index / len(csv_files) * 100
            avg_time_per_file = elapsed / index
            remaining_files = len(csv_files) - index
            estimated_remaining = avg_time_per_file * remaining_files

            try:
                line_count = line_count_cache.get(file_path, 0)
                base_ticker, quote_currency = KrakenPairParser.parse_pair(pair_name)

                if skip_existing and (base_ticker, interval) in skip_set:
                    total_skipped += 1
                    self.stdout.write(
                        f"⊘ [{index}/{len(csv_files)}] {pair_name:12} {interval:4}m - Skipped (exists) | "
                        f"{line_count:>7,} lines | {progress_pct:5.1f}% | ⏱️  {format_time(elapsed)} | ETA {format_time(estimated_remaining)}"
                    )
                    continue

                # Determine tier for this specific asset if in auto mode
                asset_tier = None
                if tier_option == "auto":
                    asset_tier = KrakenAssetCreator.determine_tier(base_ticker)

                asset = asset_creator.get_or_create_asset(base_ticker, quote_currency, tier=asset_tier)

                created = self._import_file(file_path, asset, interval, batch_size, dry_run, update_existing, database)
                total_created += created

                if not dry_run:
                    dest_path = os.path.join(ingested_dir, os.path.basename(file_path))
                    shutil.move(file_path, dest_path)
                    total_moved += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ [{index}/{len(csv_files)}] {pair_name:12} {interval:4}m - +{created:6,} | "
                        f"{line_count:>7,} lines | {progress_pct:5.1f}% | ⏱️  {format_time(elapsed)} | ETA {format_time(estimated_remaining)}"
                    )
                )

            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 60:
                    short_error = error_msg[:60]
                else:
                    short_error = error_msg
                failed_files.append((file_path, error_msg))
                line_count = line_count_cache.get(file_path, 0)
                line_info = f"{line_count:>7,} lines | " if line_count else ""
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ [{index}/{len(csv_files)}] {pair_name:12} {interval:4}m - {short_error} | "
                        f"{line_info}{progress_pct:5.1f}% | ⏱️  {format_time(elapsed)} | ETA {format_time(estimated_remaining)}"
                    )
                )

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

    def _cache_line_counts(self, csv_files):
        line_count_cache = {}
        total_files = len(csv_files)
        for idx, (file_path, pair_name, interval) in enumerate(csv_files, start=1):
            self.stdout.write(f"  [{idx}/{total_files}] Counting {pair_name} {interval}m...", ending="\r")
            self.stdout.flush()
            line_count_cache[file_path] = self._count_file_lines(file_path)
        self.stdout.write(f"✓ Counted {len(line_count_cache)} files{' ' * 50}")
        return line_count_cache

    def _build_skip_set(self, csv_files, database):
        pairs_to_check = {}
        intervals_set = set()
        for _, pair_name, interval in csv_files:
            try:
                base_ticker, _ = KrakenPairParser.parse_pair(pair_name)
                pairs_to_check[(base_ticker, interval)] = True
                intervals_set.add(interval)
            except ValueError:
                continue

        tickers = {ticker for ticker, _ in pairs_to_check.keys()}
        assets = {asset.ticker: asset.id for asset in Asset.objects.using(database).filter(ticker__in=tickers)}

        if not assets:
            return set()

        asset_ids = list(assets.values())
        intervals_list = list(intervals_set)

        existing_combinations = (
            AssetPrice.objects.using(database)
            .filter(asset_id__in=asset_ids, interval_minutes__in=intervals_list, source="kraken")
            .values_list("asset_id", "interval_minutes")
            .distinct()
        )

        asset_id_to_ticker = {v: k for k, v in assets.items()}
        skip_set = set()

        for asset_id, interval_minutes in existing_combinations:
            if asset_id in asset_id_to_ticker:
                ticker = asset_id_to_ticker[asset_id]
                skip_set.add((ticker, interval_minutes))

        return skip_set

    def _display_file_list(self, csv_files, line_count_cache):
        by_pair = {}
        for file_path, pair_name, interval in csv_files:
            if pair_name not in by_pair:
                by_pair[pair_name] = {"intervals": [], "files": []}
            by_pair[pair_name]["intervals"].append(interval)
            by_pair[pair_name]["files"].append(file_path)

        sorted_pairs = sorted(by_pair.keys())
        for pair_name in sorted_pairs:
            intervals = sorted(by_pair[pair_name]["intervals"])
            interval_str = ", ".join(f"{i}m" for i in intervals)
            total_lines = sum(line_count_cache.get(f, 0) for f in by_pair[pair_name]["files"])
            self.stdout.write(f"  • {pair_name:12} → {interval_str:30} ({total_lines:>10,} lines)")
            self.stdout.flush()

    def _count_file_lines(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) - 1

    def _discover_files(self, data_dir, intervals, pair_filter):
        csv_files = []
        for file_name in os.listdir(data_dir):
            if not file_name.endswith(".csv"):
                continue

            base_name = file_name.replace(".csv", "")

            pair_name = None
            interval_str = None

            for known_interval in self.INTERVAL_MAP.keys():
                if base_name.endswith(f"_{known_interval}"):
                    pair_name = base_name[: -len(known_interval) - 1]
                    interval_str = known_interval
                    break

            if not pair_name or not interval_str:
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

    def _import_file(self, file_path, asset, interval, batch_size, dry_run, update_existing, database):
        created_count = 0

        if dry_run:
            for _ in parse_ohlcv_csv(file_path, interval):
                created_count += 1
            return created_count

        return self._import_file_with_copy(file_path, asset, interval, batch_size, update_existing, database)

    def _import_file_with_copy(self, file_path, asset, interval, batch_size, update_existing, database):
        buffer = io.StringIO()
        created_count = 0
        now = timezone.now()
        now_iso = now.isoformat()
        asset_id = asset.id

        for data in parse_ohlcv_csv(file_path, interval):
            created_count += 1
            time_iso = data["timestamp"].isoformat()
            buffer.write(
                f"{asset_id}\t{time_iso}\t{data['open']}\t{data['high']}\t"
                f"{data['low']}\t{data['close']}\t{data['volume'] or ''}\t"
                f"{data['interval_minutes'] or ''}\t{data['trade_count'] or ''}\tkraken\t{now_iso}\n"
            )

            if created_count % batch_size == 0:
                self._execute_copy_with_staging(buffer, update_existing, database)
                buffer = io.StringIO()

        if buffer.tell() > 0:
            self._execute_copy_with_staging(buffer, update_existing, database)

        return created_count

    def _execute_copy_with_staging(self, buffer, update_existing, database):
        buffer.seek(0)
        columns = (
            "asset_id",
            "time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "interval_minutes",
            "trade_count",
            "source",
            "created_at",
        )

        with connections[database].cursor() as cursor:
            cursor.execute("""
                CREATE TEMP TABLE IF NOT EXISTS staging_assetprice (
                    asset_id BIGINT NOT NULL,
                    time TIMESTAMPTZ NOT NULL,
                    open NUMERIC NOT NULL,
                    high NUMERIC NOT NULL,
                    low NUMERIC NOT NULL,
                    close NUMERIC NOT NULL,
                    volume NUMERIC,
                    interval_minutes SMALLINT,
                    trade_count INTEGER,
                    source VARCHAR(50) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
            """)

            cursor.execute("TRUNCATE TABLE staging_assetprice")

            copy_sql = f"COPY staging_assetprice ({', '.join(columns)}) FROM STDIN"
            with cursor.cursor.copy(copy_sql) as copy:
                while True:
                    data = buffer.read(65536)
                    if not data:
                        break
                    copy.write(data)

            if update_existing:
                cursor.execute("""
                    INSERT INTO feefifofunds_assetprice
                        (asset_id, time, open, high, low, close, volume,
                         interval_minutes, trade_count, source, created_at)
                    SELECT asset_id, time, open, high, low, close, volume,
                           interval_minutes, trade_count, source, created_at
                    FROM staging_assetprice
                    ON CONFLICT (asset_id, time, source, interval_minutes)
                    DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        trade_count = EXCLUDED.trade_count,
                        created_at = EXCLUDED.created_at
                """)
            else:
                cursor.execute("""
                    INSERT INTO feefifofunds_assetprice
                        (asset_id, time, open, high, low, close, volume,
                         interval_minutes, trade_count, source, created_at)
                    SELECT asset_id, time, open, high, low, close, volume,
                           interval_minutes, trade_count, source, created_at
                    FROM staging_assetprice
                    ON CONFLICT (asset_id, time, source, interval_minutes)
                    DO NOTHING
                """)

            cursor.execute("DROP TABLE IF EXISTS staging_assetprice")

    def _filter_by_tier(self, csv_files, target_tiers):
        """Filter CSV files to only include assets matching specified tiers."""
        filtered = []
        for file_path, pair_name, interval in csv_files:
            try:
                base_ticker, _ = KrakenPairParser.parse_pair(pair_name)
                # Determine the tier this asset would be assigned
                asset_tier = KrakenAssetCreator.determine_tier(base_ticker)

                # Check if the determined tier matches any of the target tiers
                if asset_tier in target_tiers:
                    filtered.append((file_path, pair_name, interval))
            except ValueError:
                # Skip files we can't parse
                continue

        return filtered
