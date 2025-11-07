"""
Ingest Kraken OHLCV (candle) data from CSV files.

Example usage:
    # Ingest daily data only (parallel processing auto-enabled)
    python manage.py ingest_kraken_ohlcv --intervals 1440 --database timescaledb

    # Ingest only Tier 1 assets (major cryptos)
    python manage.py ingest_kraken_ohlcv --intervals 1440 --only-tier TIER1 --database timescaledb

    # Ingest hourly and daily data with custom worker count
    python manage.py ingest_kraken_ohlcv --intervals 60,1440 --workers 4 --database timescaledb

    # Skip confirmation prompt for automated runs
    python manage.py ingest_kraken_ohlcv --intervals 1440 --yes --database timescaledb

    # Update existing records instead of skipping duplicates
    python manage.py ingest_kraken_ohlcv --intervals 1440 --update-existing --database timescaledb

    # Dry run to preview what would be imported (no parallelization)
    python manage.py ingest_kraken_ohlcv --intervals 1440 --dry-run

Notes:
    - Parallel processing is automatic (uses CPU cores - 1, max 8)
    - Workers can be controlled with --workers flag if needed
    - Tier auto-detection is enabled by default
    - Currency tracking: Each price record tracks its quote currency (USD, EUR, etc.)
"""

import io
import os
import shutil
import time
from multiprocessing import Manager, Pool, cpu_count
from pathlib import Path

from django.core.management.base import BaseCommand


def _init_worker():
    """
    Initialize worker process with Django setup.
    This runs once per worker when the pool starts.
    """
    import os

    import django

    # Set Django settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    # Close any existing database connections from parent process
    # This prevents connection sharing issues
    from django.db import connections

    for conn in connections.all():
        conn.close()

    # Setup Django in this worker process
    django.setup()

    # Verify Django is ready
    from django.apps import apps

    if not apps.ready:
        raise RuntimeError("Django apps not ready after setup")


def _worker_import_file(args):
    """
    Worker function for parallel file processing.
    Must be at module level for pickling.
    Django is already initialized via _init_worker.
    """
    # Import Django modules - Django is already set up by _init_worker
    from django.utils import timezone

    from feefifofunds.services.kraken import KrakenAssetCreator, parse_ohlcv_csv

    (
        file_path,
        pair_name,
        interval,
        base_ticker,
        quote_currency,
        asset_tier,
        batch_size,
        update_existing,
        database,
        ingested_dir,
        progress_queue,
    ) = args

    try:
        # Reconstruct asset creator and get/create asset
        asset_creator = KrakenAssetCreator(database=database)
        asset = asset_creator.get_or_create_asset(base_ticker, tier=asset_tier)

        # Import the file
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
                f"{data['interval_minutes'] or ''}\t{data['trade_count'] or ''}\t{quote_currency}\tkraken\t{now_iso}\n"
            )

            if created_count % batch_size == 0:
                _execute_copy_with_staging(buffer, update_existing, database)
                buffer = io.StringIO()

        if buffer.tell() > 0:
            _execute_copy_with_staging(buffer, update_existing, database)

        # Move file to ingested directory
        dest_path = os.path.join(ingested_dir, os.path.basename(file_path))
        shutil.move(file_path, dest_path)

        # Report success
        progress_queue.put({"success": True, "file": pair_name, "created": created_count})
        return {"success": True, "created": created_count}

    except Exception as e:
        # Report error
        progress_queue.put({"success": False, "file": pair_name, "error": str(e)})
        return {"success": False, "error": str(e)}


def _execute_copy_with_staging(buffer, update_existing, database):
    """Helper function for COPY operation.
    Django is already initialized via _init_worker.
    """
    from django.db import connections

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
        "quote_currency",
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
                quote_currency VARCHAR(10) NOT NULL,
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
                     interval_minutes, trade_count, quote_currency, source, created_at)
                SELECT asset_id, time, open, high, low, close, volume,
                       interval_minutes, trade_count, quote_currency, source, created_at
                FROM staging_assetprice
                ON CONFLICT (asset_id, time, source, interval_minutes, quote_currency)
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
                     interval_minutes, trade_count, quote_currency, source, created_at)
                SELECT asset_id, time, open, high, low, close, volume,
                       interval_minutes, trade_count, quote_currency, source, created_at
                FROM staging_assetprice
                ON CONFLICT (asset_id, time, source, interval_minutes, quote_currency)
                DO NOTHING
            """)

        cursor.execute("DROP TABLE IF EXISTS staging_assetprice")


class Command(BaseCommand):
    help = """Ingest Kraken OHLCV (candle) data from CSV files.

    Features:
    - Parallel processing with multiprocessing (auto-detects CPU cores, max 8 workers)
    - Uses PostgreSQL COPY with staging table for optimal performance (50k-100k records/sec)
    - Supports upsert/update mode for re-ingestion (--update-existing)
    - Handles duplicates gracefully with ON CONFLICT DO NOTHING/UPDATE
    - Automatic tier classification based on asset ticker
    - Tier-based filtering for selective ingestion (--only-tier)
    - Real-time progress tracking with accurate ETA based on data volume
    - Automatic file moving to ingested/ directory after success
    - TimescaleDB hypertable support with automatic chunk management
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Import Django dependencies only in main process
        from django.db import connections
        from django.utils import timezone

        from feefifofunds.models import Asset, AssetPrice
        from feefifofunds.services.kraken import KrakenAssetCreator, KrakenPairParser, parse_ohlcv_csv
        from utils.time import format_time

        self.connections = connections
        self.timezone = timezone
        self.Asset = Asset
        self.AssetPrice = AssetPrice
        self.KrakenAssetCreator = KrakenAssetCreator
        self.KrakenPairParser = KrakenPairParser
        self.parse_ohlcv_csv = parse_ohlcv_csv
        self.format_time = format_time

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
            default="auto",
            choices=["TIER1", "TIER2", "TIER3", "TIER4", "UNCLASSIFIED", "auto"],
            help="Tier to assign to new assets (default: 'auto' to determine based on ticker)",
        )
        parser.add_argument(
            "--only-tier",
            type=str,
            action="append",
            choices=["TIER1", "TIER2", "TIER3", "TIER4", "UNCLASSIFIED"],
            help="Only ingest assets matching specified tier(s). Can be used multiple times.",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=None,
            help="Number of parallel workers (default: auto-detect based on CPU cores, max 8)",
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
        workers = options["workers"]

        # Smart worker count determination
        if workers is None:
            # Auto-detect: use all cores minus 1, but cap at 8 to avoid overwhelming DB
            workers = min(max(cpu_count() - 1, 1), 8)

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

        # Display parallel processing mode
        if workers > 1:
            self.stdout.write(self.style.SUCCESS(f"🚀 Parallel mode: {workers} workers"))
        else:
            self.stdout.write("🔄 Sequential mode: 1 worker")

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
        asset_creator = self.KrakenAssetCreator(database=database, default_tier=default_tier)

        if not dry_run:
            self.stdout.write("🏗️  Pre-creating assets...")
            unique_pairs = {pair_name for _, pair_name, _ in csv_files}
            unique_count = asset_creator.bulk_create_assets(list(unique_pairs))
            self.stdout.write(f"✓ Pre-created {unique_count} unique assets from {len(unique_pairs)} trading pairs")

        if skip_existing:
            self.stdout.write("🔍 Building skip-existing index...")
            skip_set = self._build_skip_set(csv_files, database)
            self.stdout.write(f"✓ Found {len(skip_set)} existing asset-interval combinations to skip")
            # Filter out files that should be skipped
            csv_files = [
                (fp, pn, iv)
                for fp, pn, iv in csv_files
                if (self.KrakenPairParser.parse_pair(pn)[0], iv) not in skip_set
            ]
            self.stdout.write(f"✓ {len(csv_files)} files remaining after skip-existing filter")

        ingested_dir = os.path.join(os.path.dirname(data_dir), "ingested", "Kraken_OHLCVT")
        if not dry_run:
            os.makedirs(ingested_dir, exist_ok=True)

        # Process files
        if dry_run:
            # Dry-run uses simplified sequential processing
            result = self._process_dry_run(csv_files, line_count_cache)
        else:
            # Production mode always uses parallel processing
            result = self._process_files_parallel(
                csv_files,
                line_count_cache,
                tier_option,
                batch_size,
                update_existing,
                database,
                ingested_dir,
                workers,
            )

        total_created = result["total_created"]
        total_moved = result["total_moved"]
        failed_files = result["failed_files"]
        elapsed_total = result["elapsed_total"]

        success_count = len(csv_files) - len(failed_files)

        self.stdout.write(f"\n{'─' * 80}")
        if not dry_run and total_moved > 0:
            self.stdout.write(f"📁 Moved {total_moved} file(s) to {ingested_dir}")
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Complete: {success_count}/{len(csv_files)} files | "
                f"+{total_created:,} records created | "
                f"⏱️  {self.format_time(elapsed_total)}"
            )
        )

        if failed_files:
            self.stdout.write(self.style.WARNING(f"\n⚠️  {len(failed_files)} files failed:"))
            for file_path, error in failed_files[:10]:
                self.stdout.write(f"  • {Path(file_path).name}: {error[:60]}")

    def _process_dry_run(self, csv_files, line_count_cache):
        """Process dry-run mode - just count lines without database operations."""
        total_created = 0
        failed_files = []
        start_time = time.time()

        for index, (file_path, pair_name, interval) in enumerate(csv_files, start=1):
            try:
                for _ in self.parse_ohlcv_csv(file_path, interval):
                    total_created += 1

                line_count = line_count_cache.get(file_path, 0)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ [{index}/{len(csv_files)}] {pair_name:12} {interval:4}m - {line_count:>7,} lines (dry-run)"
                    )
                )

            except Exception as e:
                failed_files.append((file_path, str(e)))
                self.stdout.write(
                    self.style.ERROR(f"✗ [{index}/{len(csv_files)}] {pair_name:12} {interval:4}m - {str(e)[:60]}")
                )

        elapsed_total = time.time() - start_time
        return {
            "total_created": total_created,
            "total_moved": 0,
            "failed_files": failed_files,
            "elapsed_total": elapsed_total,
        }

    def _process_files_parallel(
        self, csv_files, line_count_cache, tier_option, batch_size, update_existing, database, ingested_dir, workers
    ):
        """Process files in parallel using multiprocessing."""
        total_created = 0
        total_moved = 0
        failed_files = []
        start_time = time.time()

        total_lines = sum(line_count_cache.values())
        processed_lines = 0
        completed_files = 0

        # Prepare worker arguments
        worker_args = []
        for file_path, pair_name, interval in csv_files:
            try:
                base_ticker, quote_currency = self.KrakenPairParser.parse_pair(pair_name)

                asset_tier = None
                if tier_option == "auto":
                    asset_tier = self.KrakenAssetCreator.determine_tier(base_ticker)
                elif tier_option and tier_option != "auto":
                    asset_tier = tier_option

                worker_args.append(
                    (
                        file_path,
                        pair_name,
                        interval,
                        base_ticker,
                        quote_currency,
                        asset_tier,
                        batch_size,
                        update_existing,
                        database,
                        ingested_dir,
                        None,  # Progress queue placeholder
                    )
                )
            except ValueError as e:
                failed_files.append((file_path, str(e)))

        # Create manager and queue for progress reporting
        manager = Manager()
        progress_queue = manager.Queue()

        # Update worker args with the queue
        worker_args = [
            (
                file_path,
                pair_name,
                interval,
                base_ticker,
                quote_currency,
                asset_tier,
                batch_size,
                update_existing,
                database,
                ingested_dir,
                progress_queue,
            )
            for (
                file_path,
                pair_name,
                interval,
                base_ticker,
                quote_currency,
                asset_tier,
                batch_size,
                update_existing,
                database,
                ingested_dir,
                _,
            ) in worker_args
        ]

        self.stdout.write("")

        # Close database connections before creating pool to prevent sharing
        for conn in self.connections.all():
            conn.close()

        # Start worker pool with proper Django initialization
        with Pool(processes=workers, initializer=_init_worker) as pool:
            # Submit all tasks
            async_result = pool.map_async(_worker_import_file, worker_args, chunksize=1)

            # Monitor progress from queue
            while not async_result.ready() or not progress_queue.empty():
                try:
                    # Non-blocking queue get with timeout
                    result = progress_queue.get(timeout=0.1)
                    completed_files += 1

                    # Get line count for this file
                    file_info = next(
                        ((fp, pn, iv) for fp, pn, iv in csv_files if pn == result["file"]),
                        None,
                    )
                    if file_info:
                        line_count = line_count_cache.get(file_info[0], 0)
                        processed_lines += line_count

                    elapsed = time.time() - start_time
                    progress_pct = (
                        (processed_lines / total_lines * 100)
                        if total_lines > 0
                        else (completed_files / len(csv_files) * 100)
                    )

                    if processed_lines > 0 and elapsed > 0:
                        lines_per_sec = processed_lines / elapsed
                        remaining_lines = total_lines - processed_lines
                        estimated_remaining = remaining_lines / lines_per_sec if lines_per_sec > 0 else 0
                    else:
                        estimated_remaining = 0

                    if result["success"]:
                        total_created += result["created"]
                        total_moved += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ [{completed_files}/{len(csv_files)}] {result['file']:12} - "
                                f"+{result['created']:6,} | {progress_pct:5.1f}% | "
                                f"⏱️  {self.format_time(elapsed)} | ETA {self.format_time(estimated_remaining)}"
                            )
                        )
                    else:
                        failed_files.append((result["file"], result["error"]))
                        short_error = result["error"][:40] if len(result["error"]) > 40 else result["error"]
                        self.stdout.write(
                            self.style.ERROR(
                                f"✗ [{completed_files}/{len(csv_files)}] {result['file']:12} - "
                                f"{short_error} | {progress_pct:5.1f}% | "
                                f"⏱️  {self.format_time(elapsed)} | ETA {self.format_time(estimated_remaining)}"
                            )
                        )

                except Exception:
                    # Queue empty or timeout, continue
                    if async_result.ready():
                        break
                    time.sleep(0.1)

        elapsed_total = time.time() - start_time
        return {
            "total_created": total_created,
            "total_moved": total_moved,
            "failed_files": failed_files,
            "elapsed_total": elapsed_total,
        }

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
                base_ticker, _ = self.KrakenPairParser.parse_pair(pair_name)
                pairs_to_check[(base_ticker, interval)] = True
                intervals_set.add(interval)
            except ValueError:
                continue

        tickers = {ticker for ticker, _ in pairs_to_check.keys()}
        assets = {asset.ticker: asset.id for asset in self.Asset.objects.using(database).filter(ticker__in=tickers)}

        if not assets:
            return set()

        asset_ids = list(assets.values())
        intervals_list = list(intervals_set)

        existing_combinations = (
            self.AssetPrice.objects.using(database)
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

    def _filter_by_tier(self, csv_files, target_tiers):
        """Filter CSV files to only include assets matching specified tiers."""
        filtered = []
        for file_path, pair_name, interval in csv_files:
            try:
                base_ticker, _ = self.KrakenPairParser.parse_pair(pair_name)
                # Determine the tier this asset would be assigned
                asset_tier = self.KrakenAssetCreator.determine_tier(base_ticker)

                # Check if the determined tier matches any of the target tiers
                if asset_tier in target_tiers:
                    filtered.append((file_path, pair_name, interval))
            except ValueError:
                # Skip files we can't parse
                continue

        return filtered
