"""
Optimized sequential file ingestor management command for OHLCVT data.
Fast, simple sequential processing without state tracking.
"""

import time
import traceback
from pathlib import Path

from django.core.management.base import BaseCommand

from feefifofunds.services.sequential_ingestor import SequentialIngestor
from feefifofunds.utils.progress_reporter import ProgressReporter


class Command(BaseCommand):
    """
    Fast sequential ingestion of Kraken OHLCVT files.

    Features:
    - Filter by tier: --tier (TIER1/2/3/4/ALL)
    - Filter by file type: --file-type (ohlcv/trade/both)
    - Filter by intervals: --intervals (e.g., 60,1440 for 1h and 1d)
    - Automatic file type detection (OHLCV vs Trade)
    - Empty file deletion
    - Progress tracking with ETA
    - Move completed files to ingested/ folder
    """

    help = "Fast sequential ingestion of Kraken OHLCVT files with tier, file type, and interval filtering"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--tier",
            type=str,
            default="ALL",
            choices=["TIER1", "TIER2", "TIER3", "TIER4", "ALL"],
            help="Tier of assets to ingest (default: ALL)",
        )
        parser.add_argument(
            "--file-type",
            type=str,
            default="both",
            choices=["ohlcv", "trade", "both"],
            help="Type of files to ingest: ohlcv (candle data), trade (tick data), or both (default: both)",
        )
        parser.add_argument(
            "--intervals",
            type=str,
            help="Comma-separated list of intervals in minutes (e.g., '60,1440' for 1h and 1d). Only applies to OHLCV files. Defaults to all intervals.",
        )
        parser.add_argument(
            "--yes",
            "-y",
            action="store_true",
            help="Skip confirmation prompts",
        )
        parser.add_argument(
            "--database",
            type=str,
            default="timescaledb",
            help="Database to use (default: timescaledb)",
        )
        parser.add_argument(
            "--data-dir",
            type=str,
            help="Custom data directory (for testing)",
        )
        parser.add_argument(
            "--stop-on-error",
            action="store_true",
            help="Stop processing on first error (default: continue)",
        )

    def handle(self, *args, **options):
        """Main command execution."""
        tier_filter = options["tier"]
        file_type_filter = options["file_type"]
        intervals_str = options.get("intervals")
        skip_confirmation = options["yes"]
        database = options["database"]
        data_dir = options.get("data_dir")
        stop_on_error = options["stop_on_error"]

        # Parse intervals if provided
        interval_filter = None
        if intervals_str:
            try:
                interval_filter = [int(x.strip()) for x in intervals_str.split(",")]
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Invalid intervals format: {intervals_str}"))
                self.stdout.write(self.style.ERROR("Expected comma-separated integers, e.g., '60,1440'"))
                return

        # Initialize components
        ingestor = SequentialIngestor(database=database, data_dir=data_dir)

        # Discover files to process
        self.stdout.write("🔍 Discovering files...")
        all_files = ingestor.discover_files(tier_filter, file_type_filter, interval_filter)

        if not all_files:
            self.stdout.write(
                self.style.WARNING(
                    f"No files found matching filters (tier={tier_filter}, file_type={file_type_filter})"
                )
            )
            return

        # Calculate tier breakdown
        tier_counts = {}
        for _, _, ticker in all_files:
            from feefifofunds.services.kraken import KrakenAssetCreator

            tier = KrakenAssetCreator.determine_tier(ticker)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        # Initialize progress reporter
        reporter = ProgressReporter(tier=tier_filter, total_files=len(all_files))

        # Display summary
        reporter.display_header()

        # Show file breakdown
        self.stdout.write(f"\n📁 Files to process: {len(all_files):,}")
        self.stdout.write(f"   File type: {file_type_filter}")
        self.stdout.write(f"   Tier filter: {tier_filter}")
        if interval_filter:
            intervals_display = ", ".join(str(i) for i in interval_filter)
            self.stdout.write(f"   Interval filter: {intervals_display} minutes")

        if tier_counts:
            self.stdout.write("\n📊 Tier breakdown:")
            for tier, count in sorted(tier_counts.items()):
                self.stdout.write(f"   {tier}: {count:,} files")

        # Confirm before proceeding
        if not skip_confirmation and len(all_files) > 0:
            self.stdout.write(f"\n⚠️  This will process {len(all_files):,} files")
            self.stdout.write("   Note: Any existing data will be skipped via ON CONFLICT DO NOTHING")
            response = input("Continue? [y/N]: ")
            if response.lower() != "y":
                self.stdout.write(self.style.WARNING("Aborted"))
                return

        # Load asset cache for performance
        self.stdout.write("\n🔄 Loading asset cache...")
        ingestor.load_asset_cache()

        # Check if database has required constraints
        if not ingestor._check_unique_constraints():
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  Warning: Unique constraints not found in database."
                    "\n   This will use a slower fallback method."
                    "\n   For better performance, run: python manage.py migrate feefifofunds --database=timescaledb\n"
                )
            )

        # Optimize database for bulk operations
        self.stdout.write("⚙️  Optimizing database...")
        ingestor.optimize_database()

        # Process files sequentially
        total_records = 0
        failed_files = []

        try:
            for filepath, file_type, _ in all_files:
                # Get file size for display
                file_size = filepath.stat().st_size

                # Start file processing display
                reporter.start_file(str(filepath), file_size)

                # Process file with progress callback
                def progress_callback(records):
                    reporter.update_records(records)

                # Process the file
                try:
                    success, records, error_msg = ingestor.process_file(filepath, file_type, progress_callback)

                    if success:
                        total_records += records
                        reporter.complete_file(success=True)
                    else:
                        raise Exception(error_msg)

                except Exception as e:
                    error_trace = traceback.format_exc()
                    reporter.complete_file(success=False, error_msg=str(e))
                    reporter.display_error(str(filepath), e, error_trace)
                    failed_files.append(str(filepath))

                    if stop_on_error:
                        self.stdout.write(self.style.ERROR("\n❌ Stopping due to error (--stop-on-error flag)"))
                        break
                    else:
                        self.stdout.write(self.style.WARNING("\n⚠️  Continuing despite error..."))

        except KeyboardInterrupt:
            self.stdout.write("\n\n⚠️  Interrupted by user")

        finally:
            # Restore database settings
            self.stdout.write("\n🔄 Restoring database settings...")
            ingestor.restore_database()

        # Display final summary
        reporter.display_summary()

        # Show failed files if any
        if failed_files:
            self.stdout.write(f"\n❌ Failed files ({len(failed_files)}):")
            for filepath in failed_files[:10]:  # Show first 10
                self.stdout.write(f"   - {Path(filepath).name}")
            if len(failed_files) > 10:
                self.stdout.write(f"   ... and {len(failed_files) - 10} more")

        # Show final statistics
        processed_count = reporter.completed_files
        self.stdout.write(f"\n✅ Total completed: {processed_count:,}/{len(all_files):,} files")
        self.stdout.write(f"   Total records: {total_records:,}")

        if processed_count > 0:
            elapsed = time.time() - reporter.start_time
            avg_speed = total_records / elapsed if elapsed > 0 else 0
            self.stdout.write(f"   Average speed: {avg_speed:,.0f} records/second")

        self.stdout.write(self.style.SUCCESS("\n✨ Ingestion complete!"))
