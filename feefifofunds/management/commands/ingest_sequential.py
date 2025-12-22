import time
import traceback
from pathlib import Path

from django.core.management.base import BaseCommand

from feefifofunds.services.sequential_ingestor import SequentialIngestor
from feefifofunds.utils.progress_reporter import ProgressReporter


class Command(BaseCommand):
    help = "Fast sequential ingestion of Kraken OHLCV files with tier and interval filtering"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tier",
            type=str,
            default="ALL",
            choices=["TIER1", "TIER2", "TIER3", "TIER4", "ALL"],
            help="Tier of assets to ingest (default: ALL)",
        )
        parser.add_argument(
            "--intervals",
            type=str,
            help="Comma-separated list of intervals in minutes (e.g., '60,1440' for 1h and 1d). Defaults to all intervals.",
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
            default="questdb",
            help="Database to use (default: questdb)",
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
        tier_filter = options["tier"]
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

        ingestor = SequentialIngestor(database=database, data_dir=data_dir)

        self.stdout.write("🔍 Discovering files...")
        all_files = ingestor.discover_files(tier_filter, "ohlcv", interval_filter)

        if not all_files:
            self.stdout.write(self.style.WARNING(f"No OHLCV files found matching filters (tier={tier_filter})"))
            return

        # Calculate tier breakdown
        tier_counts = {}
        for _, _, ticker in all_files:
            from feefifofunds.services.kraken import KrakenAssetCreator

            tier = KrakenAssetCreator.determine_tier(ticker)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        reporter = ProgressReporter(tier=tier_filter, total_files=len(all_files))

        reporter.display_header()

        self.stdout.write(f"\n📁 Files to process: {len(all_files):,}")
        self.stdout.write("   File type: OHLCV")
        self.stdout.write(f"   Tier filter: {tier_filter}")
        if interval_filter:
            intervals_display = ", ".join(str(i) for i in interval_filter)
            self.stdout.write(f"   Interval filter: {intervals_display} minutes")

        if tier_counts:
            self.stdout.write("\n📊 Tier breakdown:")
            for tier, count in sorted(tier_counts.items()):
                self.stdout.write(f"   {tier}: {count:,} files")

        if not skip_confirmation and len(all_files) > 0:
            self.stdout.write(f"\n⚠️  This will process {len(all_files):,} files via QuestDB ILP")
            self.stdout.write("   Note: QuestDB deduplication enabled via UPSERT KEYS (migration 0004)")
            response = input("Continue? [y/N]: ")
            if response.lower() != "y":
                self.stdout.write(self.style.WARNING("Aborted"))
                return

        # Load asset cache for performance
        self.stdout.write("\n🔄 Loading asset cache...")
        ingestor.load_asset_cache()

        self.stdout.write("\n⚙️  Connecting to QuestDB ILP...")
        ingestor.connect_ilp()

        total_records = 0
        failed_files = []

        try:
            for filepath, file_type, _ in all_files:
                file_size = filepath.stat().st_size

                reporter.start_file(str(filepath), file_size)

                def progress_callback(records, total_in_file=0):
                    reporter.update_records(records, total_in_file if total_in_file > 0 else None)

                try:
                    success, records, error_msg = ingestor.process_file(filepath, file_type, progress_callback)

                    if success:
                        total_records += records
                        reporter.update_records(records)
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
            self.stdout.write("\n🔄 Closing ILP connection...")
            ingestor.disconnect_ilp()

        reporter.display_summary()

        if failed_files:
            self.stdout.write(f"\n❌ Failed files ({len(failed_files)}):")
            for filepath in failed_files[:10]:  # Show first 10
                self.stdout.write(f"   - {Path(filepath).name}")
            if len(failed_files) > 10:
                self.stdout.write(f"   ... and {len(failed_files) - 10} more")

        processed_count = reporter.completed_files
        self.stdout.write(f"\n✅ Total completed: {processed_count:,}/{len(all_files):,} files")
        self.stdout.write(f"   Total records: {total_records:,}")

        if processed_count > 0:
            elapsed = time.time() - reporter.start_time
            avg_speed = total_records / elapsed if elapsed > 0 else 0
            self.stdout.write(f"   Average speed: {avg_speed:,.0f} records/second")

        self.stdout.write(self.style.SUCCESS("\n✨ Ingestion complete!"))
