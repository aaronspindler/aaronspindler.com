"""
High-performance Kraken OHLCV (candle) data ingestion.

Simplified command optimized for fastest possible ingestion with automatic
parallelization, tier detection, and comprehensive progress tracking.

Example usage:
    # Ingest daily data for all tiers
    python manage.py ingest_kraken_ohlcv --intervals 1440

    # Ingest only Tier 1 assets (major cryptos like BTC, ETH)
    python manage.py ingest_kraken_ohlcv --intervals 1440 --only-tier TIER1

    # Ingest hourly and daily data for Tier 1 and Tier 2
    python manage.py ingest_kraken_ohlcv --intervals 60,1440 --only-tier TIER1 --only-tier TIER2

    # Skip confirmation prompt for automated runs
    python manage.py ingest_kraken_ohlcv --intervals 1440 --yes

    # Update existing records instead of skipping duplicates
    python manage.py ingest_kraken_ohlcv --intervals 1440 --update-existing

Features:
    - Parallel processing (auto-detects optimal worker count)
    - PostgreSQL COPY with staging tables (~350k records/sec)
    - Automatic tier detection and filtering
    - Enhanced pre-ingestion summary with tier breakdown
    - Real-time progress tracking with ETA
    - Automatic file archiving after successful ingestion
"""

import io
import os
import shutil
import time
from multiprocessing import Manager, Pool, cpu_count

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
        worker_id,
    ) = args

    # Set database for this worker (used by _init_worker for staging table)
    import os

    os.environ["KRAKEN_DB"] = database

    # Import Django modules AFTER unpacking args - Django is already set up by _init_worker
    from django.db import connections, transaction
    from django.utils import timezone

    from feefifofunds.services.kraken import KrakenAssetCreator, parse_ohlcv_csv

    try:
        # Wrap entire file processing in a single transaction for better performance
        with transaction.atomic(using=database):
            # Set async commit for this transaction (much faster, slight durability risk)
            with connections[database].cursor() as cursor:
                cursor.execute("SET LOCAL synchronous_commit TO OFF")
                cursor.execute("SET LOCAL work_mem TO '256MB'")  # More memory for sorting
                # Set generous statement timeout - UPDATE operations take longer than INSERT
                # Allow 2 seconds per 1000 records for UPDATE, 1 second for INSERT
                timeout_factor = 2000 if update_existing else 1000
                timeout_ms = max(1800000, batch_size // 1000 * timeout_factor)  # Min 30 minutes
                cursor.execute(f"SET LOCAL statement_timeout TO {timeout_ms}")

            # Reconstruct asset creator and get/create asset
            asset_creator = KrakenAssetCreator(database=database)
            asset = asset_creator.get_or_create_asset(base_ticker, tier=asset_tier)

            # Report starting work on this file
            progress_queue.put({"type": "starting", "worker_id": worker_id, "file": pair_name, "rows": 0})

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

                # Report progress every 1000 rows
                if created_count % 1000 == 0:
                    progress_queue.put(
                        {
                            "type": "partial",
                            "worker_id": worker_id,
                            "file": pair_name,
                            "rows": created_count,
                            "total_rows": batch_size,  # Estimate for progress tracking
                        }
                    )

                if created_count % batch_size == 0:
                    _execute_copy_with_staging(buffer, update_existing, database)
                    buffer = io.StringIO()

            if buffer.tell() > 0:
                _execute_copy_with_staging(buffer, update_existing, database)

            # Transaction will commit here automatically

        # Move file to ingested directory AFTER successful commit
        dest_path = os.path.join(ingested_dir, os.path.basename(file_path))
        shutil.move(file_path, dest_path)

        # Report success
        progress_queue.put({"success": True, "worker_id": worker_id, "file": pair_name, "created": created_count})
        return {"success": True, "created": created_count}

    except Exception as e:
        # Report error
        progress_queue.put({"success": False, "worker_id": worker_id, "file": pair_name, "error": str(e)})
        return {"success": False, "error": str(e)}


def _execute_copy_with_staging(buffer, update_existing, database):
    """Helper function for COPY operation.
    Django is already initialized via _init_worker.
    Staging table is pre-created in _init_worker.
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
        # Create staging table if it doesn't exist (once per connection)
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
            ) ON COMMIT PRESERVE ROWS
        """)

        # Clear the table for this batch
        cursor.execute("TRUNCATE TABLE staging_assetprice")

        copy_sql = f"COPY staging_assetprice ({', '.join(columns)}) FROM STDIN"
        with cursor.cursor.copy(copy_sql) as copy:
            # Read in larger chunks (8MB instead of 64KB) for better performance
            while True:
                data = buffer.read(8388608)  # 8MB chunks
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
    help = """High-performance Kraken OHLCV (candle) data ingestion.

    Optimized for fastest possible ingestion with:
    - Parallel processing (auto-detects optimal worker count)
    - PostgreSQL COPY with staging tables (350k+ records/sec)
    - Automatic tier detection and filtering
    - Real-time progress with accurate ETA
    - Pre-ingestion summary for approval

    Examples:
        # Ingest daily data for all tiers
        python manage.py ingest_kraken_ohlcv --intervals 1440

        # Only ingest Tier 1 assets (major cryptos)
        python manage.py ingest_kraken_ohlcv --intervals 1440 --only-tier TIER1

        # Multiple tiers and intervals
        python manage.py ingest_kraken_ohlcv --intervals 60,1440 --only-tier TIER1 --only-tier TIER2

        # Skip confirmation (for automation)
        python manage.py ingest_kraken_ohlcv --intervals 1440 --yes
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
            required=True,
            help="Comma-separated list of intervals to import (e.g., 60,1440 for hourly and daily)",
        )
        parser.add_argument(
            "--only-tier",
            type=str,
            action="append",
            choices=["TIER1", "TIER2", "TIER3", "TIER4", "UNCLASSIFIED"],
            help="Only ingest assets matching specified tier(s). Can be used multiple times.",
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

    def handle(self, *args, **options):
        # Parse user arguments
        intervals_str = options["intervals"]
        only_tiers = options["only_tier"]
        auto_approve = options["yes"]
        update_existing = options["update_existing"]

        # Hardcoded optimal settings for fastest ingestion
        OPTIMAL_BATCH_SIZE = 100000
        OPTIMAL_WORKERS = min(max(cpu_count() - 1, 1), 8)
        DATABASE = "timescaledb"
        DATA_DIR = "feefifofunds/data/kraken/Kraken_OHLCVT"
        TIER_MODE = "auto"  # Always auto-detect tier
        SKIP_EXISTING = not update_existing  # Skip by default unless updating

        # Apply hardcoded settings
        batch_size = OPTIMAL_BATCH_SIZE
        workers = OPTIMAL_WORKERS
        database = DATABASE
        data_dir = DATA_DIR
        tier_option = TIER_MODE
        skip_existing = SKIP_EXISTING

        intervals = [self.INTERVAL_MAP[i.strip()] for i in intervals_str.split(",")]

        if not os.path.exists(data_dir):
            self.stdout.write(self.style.ERROR(f"Directory not found: {data_dir}"))
            return

        csv_files = self._discover_files(data_dir, intervals)

        if not csv_files:
            self.stdout.write(self.style.WARNING("No CSV files found matching criteria"))
            return

        # Filter files based on --only-tier if specified
        if only_tiers:
            csv_files = self._filter_by_tier(csv_files, only_tiers)
            if not csv_files:
                self.stdout.write(self.style.WARNING(f"No CSV files found for tiers: {', '.join(only_tiers)}"))
                return

        # Calculate total lines for enhanced summary
        self.stdout.write("\n📊 Analyzing files...")
        line_count_cache = self._cache_line_counts(csv_files)

        # Display enhanced ingestion summary
        self._display_enhanced_summary(
            csv_files=csv_files,
            line_count_cache=line_count_cache,
            intervals=intervals,
            only_tiers=only_tiers,
            workers=workers,
        )

        if not auto_approve:
            self.stdout.write(self.style.WARNING("\n⚠️  Ready to ingest the files listed above."))
            response = input("Continue? [y/N]: ").strip().lower()
            if response not in ["y", "yes"]:
                self.stdout.write(self.style.WARNING("❌ Ingestion cancelled by user"))
                return

        # Determine default tier for asset creator (always auto)
        asset_creator = self.KrakenAssetCreator(database=database, default_tier=None)

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
        os.makedirs(ingested_dir, exist_ok=True)

        # Process files with parallel processing for optimal performance
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
        failed_files = result["failed_files"]
        elapsed_total = result["elapsed_total"]

        success_count = len(csv_files) - len(failed_files)

        # Simple completion summary
        self.stdout.write("\n" + "─" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Complete: {success_count}/{len(csv_files)} files | +{total_created:,} records | {self.format_time(elapsed_total)}"
            )
        )

        if failed_files:
            self.stdout.write(self.style.WARNING(f"⚠️  {len(failed_files)} files failed"))

    def _display_worker_progress(
        self, worker_states, total_created, completed_files, total_files, elapsed, estimated_remaining
    ):
        """Display aggregate progress on a single line."""
        # Count workers by status
        active_workers = sum(1 for s in worker_states.values() if s["status"] == "processing")

        # Calculate cumulative rows in progress
        in_progress_rows = sum(s["rows"] for s in worker_states.values() if s["status"] == "processing")

        # Format total (including in-progress)
        display_total = total_created + in_progress_rows
        if display_total < 1000:
            total_str = f"+{display_total}"
        elif display_total < 1000000:
            total_str = f"+{display_total/1000:.1f}K"
        else:
            total_str = f"+{display_total/1e6:.1f}M"

        progress_pct = (completed_files / total_files * 100) if total_files > 0 else 0
        eta_str = f"ETA {self.format_time(estimated_remaining)}" if estimated_remaining > 0 else "Processing..."

        # Build status line
        status_line = (
            f"\r[{progress_pct:5.1f}%] {completed_files}/{total_files} files | "
            f"{active_workers} active workers | "
            f"{total_str:>8} rows | {eta_str}          "
        )

        self.stdout.write(status_line)
        self.stdout.flush()

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

        # Track state for each worker
        worker_states = {i: {"status": "idle", "file": "", "rows": 0} for i in range(workers)}

        # Prepare worker arguments
        worker_args = []
        for idx, (file_path, pair_name, interval) in enumerate(csv_files):
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
                        idx % workers,  # Worker ID (round-robin assignment)
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
                worker_id,
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
                worker_id,
            ) in worker_args
        ]

        # Close database connections before creating pool to prevent sharing
        for conn in self.connections.all():
            conn.close()

        self.stdout.write("\n🔄 Processing files...")

        # Start worker pool with proper Django initialization
        with Pool(processes=workers, initializer=_init_worker) as pool:
            # Submit all tasks
            async_result = pool.map_async(_worker_import_file, worker_args, chunksize=1)

            # Monitor progress from queue
            while not async_result.ready() or not progress_queue.empty():
                try:
                    # Non-blocking queue get with timeout
                    result = progress_queue.get(timeout=0.1)
                    worker_id = result.get("worker_id", 0)

                    # Handle different message types
                    msg_type = result.get("type")

                    if msg_type == "starting":
                        # Worker starting on a new file
                        worker_states[worker_id]["status"] = "processing"
                        worker_states[worker_id]["file"] = result["file"]
                        worker_states[worker_id]["rows"] = 0
                    elif msg_type == "partial":
                        # Progress update every 1000 rows
                        worker_states[worker_id]["status"] = "processing"
                        worker_states[worker_id]["file"] = result["file"]
                        worker_states[worker_id]["rows"] = result["rows"]
                    else:
                        # Handle file completion
                        completed_files += 1

                        # Get line count for this file
                        file_info = next(
                            ((fp, pn, iv) for fp, pn, iv in csv_files if pn == result["file"]),
                            None,
                        )
                        if file_info:
                            line_count = line_count_cache.get(file_info[0], 0)
                            processed_lines += line_count

                        if result.get("success"):
                            total_created += result["created"]
                            total_moved += 1
                            # Show completed status briefly, then back to idle
                            worker_states[worker_id] = {
                                "status": "completed",
                                "file": result["file"],
                                "rows": result["created"],
                            }
                        else:
                            failed_files.append((result["file"], result.get("error", "Unknown error")))
                            # Show failed status briefly, then back to idle
                            worker_states[worker_id] = {"status": "failed", "file": result["file"], "rows": 0}

                    # Calculate ETA
                    elapsed = time.time() - start_time
                    if processed_lines > 0 and elapsed > 0:
                        lines_per_sec = processed_lines / elapsed
                        remaining_lines = total_lines - processed_lines
                        estimated_remaining = remaining_lines / lines_per_sec if lines_per_sec > 0 else 0
                    else:
                        estimated_remaining = 0

                    # Update display
                    self._display_worker_progress(
                        worker_states, total_created, completed_files, len(csv_files), elapsed, estimated_remaining
                    )

                except Exception:
                    # Queue empty or timeout
                    if async_result.ready():
                        break

                    # Update display periodically even without new messages
                    elapsed = time.time() - start_time
                    if processed_lines > 0:
                        lines_per_sec = processed_lines / elapsed
                        remaining_lines = total_lines - processed_lines
                        estimated_remaining = remaining_lines / lines_per_sec if lines_per_sec > 0 else 0
                    else:
                        estimated_remaining = 0

                    self._display_worker_progress(
                        worker_states, total_created, completed_files, len(csv_files), elapsed, estimated_remaining
                    )
                    time.sleep(0.1)

        # Move to new line after progress display
        self.stdout.write("\n")

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
        for idx, (file_path, _, _) in enumerate(csv_files, start=1):
            self.stdout.write(f"\r  Analyzing... {idx}/{total_files}", ending="")
            self.stdout.flush()
            line_count_cache[file_path] = self._count_file_lines(file_path)
        self.stdout.write(f"\r✓ Analyzed {len(line_count_cache)} files{' ' * 20}")
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

    def _display_enhanced_summary(self, csv_files, line_count_cache, intervals, only_tiers, workers):
        """Display concise ingestion summary."""

        # Calculate statistics
        total_lines = sum(line_count_cache.values())
        total_files = len(csv_files)

        # Group by tier
        tier_counts = {}
        for _, pair_name, _ in csv_files:
            try:
                base_ticker, _ = self.KrakenPairParser.parse_pair(pair_name)
                tier = self.KrakenAssetCreator.determine_tier(base_ticker)
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
            except ValueError:
                continue

        # Time estimate
        processing_rate = 350000
        estimated_minutes = total_lines / processing_rate
        if estimated_minutes < 60:
            time_str = f"~{int(estimated_minutes)} minutes"
        else:
            hours = int(estimated_minutes / 60)
            minutes = int(estimated_minutes % 60)
            time_str = f"~{hours}h {minutes}m"

        # Display concise summary
        self.stdout.write("\n" + "─" * 60)
        self.stdout.write(f"📊 Ready to ingest {total_files:,} files | ~{total_lines/1e6:.1f}M records | {time_str}")
        self.stdout.write(f"   Intervals: {', '.join(map(str, intervals))} min | Workers: {workers}")

        # Show tier breakdown if applicable
        if tier_counts:
            tier_str = " | ".join(f"{tier}: {tier_counts[tier]}" for tier in sorted(tier_counts.keys()))
            self.stdout.write(f"   Tiers: {tier_str}")

        if only_tiers:
            self.stdout.write(f"   Filter: {', '.join(only_tiers)} only")

        self.stdout.write("─" * 60)

    def _count_file_lines(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) - 1

    def _discover_files(self, data_dir, intervals):
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
