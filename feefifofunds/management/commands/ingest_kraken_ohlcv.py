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
                timeout_ms = max(600000, batch_size // 1000 * timeout_factor)  # Min 10 minutes
                cursor.execute(f"SET LOCAL statement_timeout TO {timeout_ms}")

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

            # Transaction will commit here automatically

        # Move file to ingested directory AFTER successful commit
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

        # Calculate total lines and tier breakdown for enhanced summary
        self.stdout.write("\n📊 Analyzing files and calculating estimates...")
        line_count_cache = self._cache_line_counts(csv_files)

        # Display enhanced ingestion summary
        self._display_enhanced_summary(
            csv_files=csv_files,
            line_count_cache=line_count_cache,
            intervals=intervals,
            only_tiers=only_tiers,
            workers=workers,
            batch_size=batch_size,
            update_existing=update_existing,
        )

        if not auto_approve:
            self.stdout.write(self.style.WARNING("\n⚠️  Ready to ingest the files listed above."))
            response = input("Continue? [y/N]: ").strip().lower()
            if response not in ["y", "yes"]:
                self.stdout.write(self.style.WARNING("❌ Ingestion cancelled by user"))
                return

        self.stdout.write("")

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
        total_moved = result["total_moved"]
        failed_files = result["failed_files"]
        elapsed_total = result["elapsed_total"]

        success_count = len(csv_files) - len(failed_files)

        self.stdout.write(f"\n{'─' * 80}")
        if total_moved > 0:
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

                    # Calculate progress bar
                    bar_width = 40
                    filled = int(bar_width * progress_pct / 100)
                    bar = "█" * filled + "░" * (bar_width - filled)

                    if result["success"]:
                        total_created += result["created"]
                        total_moved += 1

                        # Enhanced progress display with bar
                        self.stdout.write(
                            f"\r🔄 INGESTION PROGRESS\n"
                            f"[{bar}] {progress_pct:5.1f}% | {completed_files:,}/{len(csv_files):,}\n"
                            f"\n"
                            + self.style.SUCCESS(
                                f"✓ [{completed_files}/{len(csv_files)}] {result['file']:12} "
                                f"+{result['created']:,} | ⏱️ {self.format_time(elapsed)} | "
                                f"ETA {self.format_time(estimated_remaining)}"
                            )
                        )

                        # Show current processing rate
                        if elapsed > 0:
                            current_rate = int(total_created / elapsed * 60)
                            self.stdout.write(
                                f"Current: {current_rate:,} records/min | "
                                f"Files: {completed_files:,}/{len(csv_files):,} | "
                                f"Records: {total_created/1e6:.1f}M/{total_lines/1e6:.1f}M"
                            )
                    else:
                        failed_files.append((result["file"], result["error"]))
                        short_error = result["error"][:40] if len(result["error"]) > 40 else result["error"]

                        self.stdout.write(
                            f"\r🔄 INGESTION PROGRESS\n"
                            f"[{bar}] {progress_pct:5.1f}% | {completed_files:,}/{len(csv_files):,}\n"
                            f"\n"
                            + self.style.ERROR(
                                f"✗ [{completed_files}/{len(csv_files)}] {result['file']:12} " f"ERROR: {short_error}"
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

    def _display_enhanced_summary(
        self, csv_files, line_count_cache, intervals, only_tiers, workers, batch_size, update_existing
    ):
        """Display comprehensive ingestion summary with tier breakdown and time estimates."""

        # Calculate statistics
        total_lines = sum(line_count_cache.values())
        total_files = len(csv_files)

        # Group by tier for breakdown
        tier_stats = {}
        for file_path, pair_name, interval in csv_files:
            try:
                base_ticker, _ = self.KrakenPairParser.parse_pair(pair_name)
                tier = self.KrakenAssetCreator.determine_tier(base_ticker)

                if tier not in tier_stats:
                    tier_stats[tier] = {"files": 0, "lines": 0, "tickers": set(), "largest_files": []}

                lines = line_count_cache.get(file_path, 0)
                tier_stats[tier]["files"] += 1
                tier_stats[tier]["lines"] += lines
                tier_stats[tier]["tickers"].add(base_ticker)
                tier_stats[tier]["largest_files"].append((pair_name, interval, lines))

            except ValueError:
                continue

        # Sort largest files in each tier
        for tier in tier_stats:
            tier_stats[tier]["largest_files"].sort(key=lambda x: x[2], reverse=True)

        # Display header
        self.stdout.write("\n" + "═" * 80)
        self.stdout.write("                    KRAKEN OHLCV DATA INGESTION".center(80))
        self.stdout.write("═" * 80)

        # Ingestion summary
        self.stdout.write("\n📊 INGESTION SUMMARY")
        self.stdout.write("─" * 40)
        self.stdout.write(f"  Files Found:     {total_files:,} files")
        self.stdout.write(f"  Intervals:       {', '.join(map(str, intervals))} minutes")
        if only_tiers:
            self.stdout.write(f"  Tiers:          {', '.join(only_tiers)} only")
        else:
            self.stdout.write("  Tiers:          All tiers")
        self.stdout.write(f"  Total Lines:     {total_lines:,} (~{total_lines/1e6:.1f}M records)")

        # Performance settings
        self.stdout.write("\n🚀 PERFORMANCE SETTINGS")
        self.stdout.write("─" * 40)
        self.stdout.write(f"  Mode:           Parallel ({workers} workers)")
        self.stdout.write(f"  Batch Size:     {batch_size:,} records")
        self.stdout.write("  Database:       TimescaleDB")
        if update_existing:
            self.stdout.write("  Duplicates:     Update existing")
        else:
            self.stdout.write("  Duplicates:     Skip existing")

        # Tier breakdown
        if tier_stats:
            self.stdout.write("\n📈 TIER BREAKDOWN")
            self.stdout.write("─" * 40)

            tier_descriptions = {
                "TIER1": "Major",
                "TIER2": "Established",
                "TIER3": "Emerging",
                "TIER4": "Small/Speculative",
                "UNCLASSIFIED": "Unclassified",
            }

            for tier in ["TIER1", "TIER2", "TIER3", "TIER4", "UNCLASSIFIED"]:
                if tier in tier_stats:
                    stats = tier_stats[tier]
                    desc = tier_descriptions.get(tier, tier)
                    self.stdout.write(
                        f"  {tier} ({desc}): {stats['files']:>4} files | " f"{stats['lines']/1e6:.1f}M lines"
                    )

                    # Show sample tickers for this tier
                    sample_tickers = sorted(list(stats["tickers"]))[:8]
                    if sample_tickers:
                        ticker_str = ", ".join(sample_tickers)
                        if len(stats["tickers"]) > 8:
                            ticker_str += f" (+{len(stats['tickers']) - 8} more)"
                        self.stdout.write(f"    • {ticker_str}")

        # Time estimate
        self.stdout.write("\n⏱️  ESTIMATED TIME")
        self.stdout.write("─" * 40)
        # Estimate based on ~350k records/minute with parallel processing
        processing_rate = 350000
        estimated_minutes = total_lines / processing_rate

        if estimated_minutes < 60:
            time_str = f"~{int(estimated_minutes)} minutes"
        else:
            hours = int(estimated_minutes / 60)
            minutes = int(estimated_minutes % 60)
            time_str = f"~{hours}h {minutes}m"

        self.stdout.write(f"  Processing Rate: ~{processing_rate:,} records/minute")
        self.stdout.write(f"  Estimated Time:  {time_str}")

        # Top files by size
        self.stdout.write("\n📋 FILES TO PROCESS (Top 10 by size)")
        self.stdout.write("─" * 40)

        # Get top 10 largest files
        files_with_sizes = [(fp, pn, iv, line_count_cache.get(fp, 0)) for fp, pn, iv in csv_files]
        files_with_sizes.sort(key=lambda x: x[3], reverse=True)

        for i, (_, pair_name, interval, lines) in enumerate(files_with_sizes[:10], 1):
            self.stdout.write(f"  {i:2}. {pair_name}_{interval}.csv".ljust(30) + f"{lines:>10,} lines")

        if len(files_with_sizes) > 10:
            self.stdout.write(f"  ... and {len(files_with_sizes) - 10:,} more files")

        self.stdout.write("")

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
