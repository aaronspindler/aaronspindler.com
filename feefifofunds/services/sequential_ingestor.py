"""
High-performance sequential file ingestor for OHLCV data.
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
    Optimized sequential ingestor for OHLCV files.
    Uses QuestDB's native ILP (InfluxDB Line Protocol) with auto-flush for maximum performance.
    """

    MIN_FILE_SIZE = 100

    def __init__(self, database: str = "questdb", data_dir: Optional[str] = None):
        """Initialize the sequential ingestor."""
        self.database = database
        self.data_dir = data_dir
        self.asset_cache: Dict[str, Asset] = {}
        self.ilp_host, self.ilp_port = self._get_ilp_connection()
        self.ilp_conf = None
        self.ingested_dir = None  # Cache ingested directory path
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

    def connect_ilp(self):
        """Store ILP connection configuration for later use.

        Auto-flush is handled by QuestDB server based on configuration:
        - Commit interval: 2000ms (from line.tcp.commit.interval.default)
        - Maintenance job interval: 5000ms

        Note: We store the config instead of creating a persistent connection
        because TCP connections don't support explicit flush() and need to be
        managed with context managers.
        """
        self.ilp_conf = f"tcp::addr={self.ilp_host}:{self.ilp_port};"

    def disconnect_ilp(self):
        """Clean up ILP configuration."""
        self.ilp_conf = None

    def _get_data_directories(self) -> Dict[str, Path]:
        """Get the data directories for OHLCV files."""
        base_dir = Path(settings.BASE_DIR)

        if self.data_dir:
            kraken_dir = Path(self.data_dir)
        else:
            kraken_dir = base_dir / "feefifofunds" / "data" / "kraken"

        return {
            "ohlcv": kraken_dir / "Kraken_OHLCVT",
            "ingested": kraken_dir / "ingested",
        }

    def _ensure_ingested_directory(self) -> Path:
        """Ensure the ingested directory exists."""
        dirs = self._get_data_directories()
        ingested_dir = dirs["ingested"]
        ingested_dir.mkdir(parents=True, exist_ok=True)

        (ingested_dir / "ohlcv").mkdir(exist_ok=True)

        return ingested_dir

    def discover_files(
        self,
        tier_filter: Optional[str] = None,
        file_type_filter: str = "ohlcv",
        interval_filter: Optional[List[int]] = None,
    ) -> List[Tuple[Path, str, str]]:
        """
        Discover all OHLCV files to process, optionally filtered by tier and intervals.

        Args:
            tier_filter: Filter by asset tier (TIER1/2/3/4/ALL)
            file_type_filter: File type filter (currently only 'ohlcv' is supported)
            interval_filter: Filter by intervals in minutes (e.g., [60, 1440])

        Returns:
            List of tuples: (filepath, file_type, ticker)
        """
        files = []
        dirs = self._get_data_directories()

        if dirs["ohlcv"].exists():
            for filepath in dirs["ohlcv"].glob("*.csv"):
                filename = filepath.stem

                if "Daily_OHLC" in filename:
                    continue

                parts = filename.split("_")
                if len(parts) >= 2:
                    pair_name = parts[0]
                    interval_str = parts[1]

                    if interval_filter:
                        try:
                            interval = int(interval_str)
                            if interval not in interval_filter:
                                continue
                        except ValueError:
                            continue

                    try:
                        base_ticker, _ = KrakenPairParser.parse_pair(pair_name)

                        if tier_filter and tier_filter != "ALL":
                            asset_tier = KrakenAssetCreator.determine_tier(base_ticker)
                            if asset_tier != tier_filter:
                                continue

                        files.append((filepath, "ohlcv", base_ticker))
                    except ValueError:
                        continue

        # Sort files for optimal processing
        # 1. Group by ticker (cache efficiency)
        # 2. Within ticker, sort by size (quick wins first)
        # Cache file sizes to avoid multiple stat calls
        files_with_size = [(f[0], f[1], f[2], f[0].stat().st_size) for f in files]
        files_with_size.sort(key=lambda x: (x[2], x[3]))
        files = [(f[0], f[1], f[2]) for f in files_with_size]

        return files

    def _check_empty_file(self, filepath: Path) -> bool:
        """Check if file is empty or too small to be valid."""
        file_size = filepath.stat().st_size
        if file_size < self.MIN_FILE_SIZE:
            return True

        # More efficient: check first two lines without loading entire file
        with open(filepath, "r") as f:
            if not f.readline():  # Empty file
                return True
            if not f.readline():  # Only header line
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
        # Quick numeric check first (most common case)
        first_field = line.split(",", 1)[0].strip()
        if first_field and first_field[0].isdigit():
            return False

        # Fallback to keyword check
        line_lower = line.lower()
        return any(
            keyword in line_lower
            for keyword in ("time", "timestamp", "open", "high", "low", "close", "volume", "price", "count", "trade")
        )

    def process_ohlcv_file(
        self,
        filepath: Path,
        asset: Asset,
        interval_minutes: int,
        quote_currency: str,
        total_lines: int = 0,
        progress_callback=None,
    ) -> int:
        """
        Process a single OHLCV file using QuestDB ILP protocol with auto-flush.

        Uses a context manager to ensure data is properly flushed on completion.

        Returns:
            Number of records inserted
        """
        if self.ilp_conf is None:
            raise RuntimeError("ILP connection not initialized. Call connect_ilp() first.")

        records_inserted = 0

        try:
            with Sender.from_conf(self.ilp_conf) as sender:
                with open(filepath, "r", buffering=8192) as csvfile:
                    # Check and skip header if present
                    first_line = csvfile.readline()
                    has_header = self._is_header_line(first_line)
                    if not has_header:
                        csvfile.seek(0)

                    reader = csv.reader(csvfile)

                    for row in reader:
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

                        records_inserted += 1

                        if progress_callback and records_inserted % 10000 == 0:
                            progress_callback(records_inserted, total_lines)

                # Context manager will auto-flush on exit

        except Exception:
            raise

        return records_inserted

    def process_file(self, filepath: Path, file_type: str, progress_callback=None) -> Tuple[bool, int, Optional[str]]:
        """
        Process a single OHLCV file.

        Returns:
            Tuple of (success, records_processed, error_message)
        """
        try:
            if self._check_empty_file(filepath):
                self._delete_empty_file(filepath)
                return True, 0, "Empty file deleted"

            filename = filepath.stem
            parts = filename.split("_")
            if len(parts) < 2:
                return False, 0, f"Invalid OHLCV filename: {filename}"

            pair_name = parts[0]
            interval_minutes = int(parts[1])

            base_ticker, quote_currency = KrakenPairParser.parse_pair(pair_name)

            asset = self._get_or_create_asset(base_ticker, pair_name)

            records_inserted = self.process_ohlcv_file(
                filepath, asset, interval_minutes, quote_currency, 0, progress_callback
            )

            # Cache ingested directory on first use
            if self.ingested_dir is None:
                self.ingested_dir = self._ensure_ingested_directory()
            target_dir = self.ingested_dir / file_type
            target_path = target_dir / filepath.name

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
