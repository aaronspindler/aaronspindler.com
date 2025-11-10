"""
High-performance sequential file ingestor for OHLCVT data.
Uses QuestDB's native ILP (InfluxDB Line Protocol) for maximum performance.
"""

import csv
import os
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from django.conf import settings
from questdb.ingress import Sender, TimestampNanos

from feefifofunds.models import Asset
from feefifofunds.services.kraken import KrakenAssetCreator, KrakenPairParser


class SequentialIngestor:
    """
    Optimized sequential ingestor for OHLCVT files.
    Uses QuestDB's native ILP (InfluxDB Line Protocol) for maximum performance.
    """

    # Batch size for ILP flush operations (100k records for optimal performance)
    BATCH_SIZE = 100_000

    # Minimum file size to process (skip empty/header-only files)
    MIN_FILE_SIZE = 100

    def __init__(self, database: str = "questdb", data_dir: Optional[str] = None):
        """Initialize the sequential ingestor."""
        self.database = database
        self.data_dir = data_dir
        self.asset_cache: Dict[str, Asset] = {}
        self.ilp_host, self.ilp_port = self._get_ilp_connection()
        self.stats = {
            "files_processed": 0,
            "records_inserted": 0,
            "files_deleted": 0,
            "files_skipped": 0,
            "total_time": 0,
        }

    def _get_ilp_connection(self) -> Tuple[str, int]:
        """Extract ILP connection details from QUESTDB_URL environment variable."""
        questdb_url = os.environ.get("QUESTDB_URL", "")
        if questdb_url:
            parsed = urlparse(questdb_url)
            host = parsed.hostname or "localhost"
            return host, 9009
        return "localhost", 9009

    def _get_data_directories(self) -> Dict[str, Path]:
        """Get the data directories for OHLCV and Trade files."""
        base_dir = Path(settings.BASE_DIR)

        if self.data_dir:
            # Use custom data directory for testing
            kraken_dir = Path(self.data_dir)
        else:
            kraken_dir = base_dir / "feefifofunds" / "data" / "kraken"

        return {
            "ohlcv": kraken_dir / "Kraken_OHLCVT",
            "trades": kraken_dir / "Kraken_Trading_History",
            "ingested": kraken_dir / "ingested",
        }

    def _ensure_ingested_directory(self) -> Path:
        """Ensure the ingested directory exists."""
        dirs = self._get_data_directories()
        ingested_dir = dirs["ingested"]
        ingested_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for organization
        (ingested_dir / "ohlcv").mkdir(exist_ok=True)
        (ingested_dir / "trade").mkdir(exist_ok=True)

        return ingested_dir

    def discover_files(
        self,
        tier_filter: Optional[str] = None,
        file_type_filter: str = "both",
        interval_filter: Optional[List[int]] = None,
    ) -> List[Tuple[Path, str, str]]:
        """
        Discover all files to process, optionally filtered by tier, file type, and intervals.

        Args:
            tier_filter: Filter by asset tier (TIER1/2/3/4/ALL)
            file_type_filter: Filter by file type ('ohlcv', 'trade', or 'both')
            interval_filter: Filter by intervals in minutes (e.g., [60, 1440]). Only applies to OHLCV files.

        Returns:
            List of tuples: (filepath, file_type, ticker)
        """
        files = []
        dirs = self._get_data_directories()

        # Process OHLCV files (if requested)
        if file_type_filter in ("ohlcv", "both") and dirs["ohlcv"].exists():
            for filepath in dirs["ohlcv"].glob("*.csv"):
                # Parse filename to get ticker
                filename = filepath.stem  # Remove .csv

                # Skip special case files for now
                if "Daily_OHLC" in filename:
                    continue

                parts = filename.split("_")
                if len(parts) >= 2:
                    pair_name = parts[0]
                    interval_str = parts[1]

                    # Apply interval filter if specified
                    if interval_filter:
                        try:
                            interval = int(interval_str)
                            if interval not in interval_filter:
                                continue
                        except ValueError:
                            continue

                    try:
                        base_ticker, _ = KrakenPairParser.parse_pair(pair_name)

                        # Apply tier filter if specified
                        if tier_filter and tier_filter != "ALL":
                            asset_tier = KrakenAssetCreator.determine_tier(base_ticker)
                            if asset_tier != tier_filter:
                                continue

                        files.append((filepath, "ohlcv", base_ticker))
                    except ValueError:
                        # Skip unparseable files
                        continue

        # Process Trade files (if requested)
        if file_type_filter in ("trade", "both") and dirs["trades"].exists():
            for filepath in dirs["trades"].glob("*.csv"):
                # Parse filename to get ticker
                pair_name = filepath.stem  # Remove .csv
                try:
                    base_ticker, _ = KrakenPairParser.parse_pair(pair_name)

                    # Apply tier filter if specified
                    if tier_filter and tier_filter != "ALL":
                        asset_tier = KrakenAssetCreator.determine_tier(base_ticker)
                        if asset_tier != tier_filter:
                            continue

                    files.append((filepath, "trade", base_ticker))
                except ValueError:
                    # Skip unparseable files
                    continue

        # Sort files for optimal processing
        # 1. Group by ticker (cache efficiency)
        # 2. Within ticker, sort by size (quick wins first)
        files.sort(key=lambda x: (x[2], x[0].stat().st_size))

        return files

    def _check_empty_file(self, filepath: Path) -> bool:
        """Check if file is empty or too small to be valid."""
        file_size = filepath.stat().st_size
        if file_size < self.MIN_FILE_SIZE:
            return True

        # Also check if file only contains header
        with open(filepath, "r") as f:
            lines = f.readlines()
            # If file has <= 1 line (header only or empty)
            if len(lines) <= 1:
                return True

        return False

    def _delete_empty_file(self, filepath: Path) -> None:
        """Delete an empty file."""
        filepath.unlink()
        self.stats["files_deleted"] += 1

    def load_asset_cache(self) -> None:
        """Load all assets into memory cache for fast lookups."""
        self.asset_cache = {asset.ticker: asset for asset in Asset.objects.all()}

    def _get_or_create_asset(self, ticker: str, pair_name: str) -> Asset:
        """Get asset from cache or create if needed. Router handles database selection."""
        if ticker not in self.asset_cache:
            asset_creator = KrakenAssetCreator()
            asset_creator.bulk_create_assets([pair_name])
            asset = asset_creator.get_or_create_asset(ticker)
            self.asset_cache[ticker] = asset

        return self.asset_cache[ticker]

    def _is_header_line(self, line: str) -> bool:
        """Check if a CSV line is a header based on content."""
        # Common header keywords to check for
        header_keywords = ["time", "timestamp", "open", "high", "low", "close", "volume", "price", "count", "trade"]

        # Convert to lowercase for comparison
        line_lower = line.lower()

        # Check if any header keyword is in the line
        for keyword in header_keywords:
            if keyword in line_lower:
                return True

        # Try to parse as timestamp - if it fails, might be header
        first_field = line.split(",")[0].strip()
        try:
            # Try to convert to float (timestamps can be floats)
            float(first_field)
            return False  # It's a number, not a header
        except ValueError:
            return True  # Not a number, likely a header

    def process_ohlcv_file(
        self,
        filepath: Path,
        asset: Asset,
        interval_minutes: int,
        quote_currency: str,
        progress_callback=None,
    ) -> int:
        """
        Process a single OHLCV file using QuestDB ILP protocol.

        Returns:
            Number of records inserted
        """
        records_inserted = 0
        batch_count = 0

        with Sender.from_conf(f"tcp::addr={self.ilp_host}:{self.ilp_port};") as sender:
            with open(filepath, "r") as csvfile:
                first_line = csvfile.readline()
                if self._is_header_line(first_line):
                    pass
                else:
                    csvfile.seek(0)

                reader = csv.reader(csvfile)

                for row_num, row in enumerate(reader, 1):
                    if len(row) < 6:
                        continue

                    timestamp = datetime.fromtimestamp(float(row[0]), tz=timezone.utc)
                    open_price = float(row[1])
                    high_price = float(row[2])
                    low_price = float(row[3])
                    close_price = float(row[4])
                    volume = float(row[5]) if row[5] else 0.0
                    trade_count = int(row[6]) if len(row) > 6 and row[6] else 0

                    sender.row(
                        "assetprice",
                        symbols={"quote_currency": quote_currency, "source": "kraken"},
                        columns={
                            "asset_id": asset.id,
                            "open": open_price,
                            "high": high_price,
                            "low": low_price,
                            "close": close_price,
                            "volume": volume,
                            "interval_minutes": interval_minutes,
                            "trade_count": trade_count,
                        },
                        at=TimestampNanos.from_datetime(timestamp),
                    )

                    batch_count += 1
                    records_inserted += 1

                    if batch_count >= self.BATCH_SIZE:
                        sender.flush()
                        batch_count = 0

                        if progress_callback and row_num % 10000 == 0:
                            progress_callback(row_num)

                if batch_count > 0:
                    sender.flush()

        return records_inserted

    def process_trade_file(self, filepath: Path, asset: Asset, quote_currency: str, progress_callback=None) -> int:
        """
        Process a single trade file using QuestDB ILP protocol.

        Returns:
            Number of records inserted
        """
        records_inserted = 0
        batch_count = 0

        with Sender.from_conf(f"tcp::addr={self.ilp_host}:{self.ilp_port};") as sender:
            with open(filepath, "r") as csvfile:
                first_line = csvfile.readline()
                if self._is_header_line(first_line):
                    pass
                else:
                    csvfile.seek(0)

                reader = csv.reader(csvfile)

                for row_num, row in enumerate(reader, 1):
                    if len(row) < 3:
                        continue

                    timestamp = datetime.fromtimestamp(float(row[0]), tz=timezone.utc)
                    price = float(row[1])
                    volume = float(row[2])

                    sender.row(
                        "trade",
                        symbols={"quote_currency": quote_currency, "source": "kraken"},
                        columns={"asset_id": asset.id, "price": price, "volume": volume},
                        at=TimestampNanos.from_datetime(timestamp),
                    )

                    batch_count += 1
                    records_inserted += 1

                    if batch_count >= self.BATCH_SIZE:
                        sender.flush()
                        batch_count = 0

                        if progress_callback and row_num % 10000 == 0:
                            progress_callback(row_num)

                if batch_count > 0:
                    sender.flush()

        return records_inserted

    def process_file(self, filepath: Path, file_type: str, progress_callback=None) -> Tuple[bool, int, Optional[str]]:
        """
        Process a single file.

        Returns:
            Tuple of (success, records_processed, error_message)
        """
        try:
            # Check if file is empty
            if self._check_empty_file(filepath):
                self._delete_empty_file(filepath)
                return True, 0, "Empty file deleted"

            # Parse file details
            if file_type == "ohlcv":
                # Parse OHLCV filename: PAIR_INTERVAL.csv
                filename = filepath.stem
                parts = filename.split("_")
                if len(parts) < 2:
                    return False, 0, f"Invalid OHLCV filename: {filename}"

                pair_name = parts[0]
                interval_minutes = int(parts[1])
            else:
                # Parse trade filename: PAIR.csv
                pair_name = filepath.stem
                interval_minutes = None

            # Parse pair to get ticker and quote currency
            base_ticker, quote_currency = KrakenPairParser.parse_pair(pair_name)

            # Get or create asset
            asset = self._get_or_create_asset(base_ticker, pair_name)

            # Process file based on type
            if file_type == "ohlcv":
                records_inserted = self.process_ohlcv_file(
                    filepath, asset, interval_minutes, quote_currency, progress_callback
                )
            else:
                records_inserted = self.process_trade_file(filepath, asset, quote_currency, progress_callback)

            # Move file to ingested directory
            ingested_dir = self._ensure_ingested_directory()
            target_dir = ingested_dir / file_type
            target_path = target_dir / filepath.name

            # Handle duplicate filenames
            if target_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_path = target_dir / f"{filepath.stem}_{timestamp}.csv"

            shutil.move(str(filepath), str(target_path))

            self.stats["files_processed"] += 1
            self.stats["records_inserted"] += records_inserted

            return True, records_inserted, None

        except Exception:
            error_trace = traceback.format_exc()
            return False, 0, error_trace

    def optimize_database(self):
        """
        Run database optimizations before bulk ingestion.

        QuestDB doesn't support PostgreSQL's work_mem or autovacuum settings.
        QuestDB is optimized for writes by default, so no configuration needed.
        """
        pass

    def restore_database(self):
        """
        Restore database settings after bulk ingestion.

        QuestDB doesn't support VACUUM or ANALYZE commands.
        QuestDB handles storage optimization automatically.
        """
        pass
