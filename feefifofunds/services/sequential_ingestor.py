"""
High-performance sequential file ingestor for OHLCVT data.
Optimized for speed with direct COPY operations and minimal overhead.
"""

import csv
import shutil
import traceback
from datetime import datetime, timezone
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.db import connections

from feefifofunds.models import Asset
from feefifofunds.services.kraken import KrakenAssetCreator, KrakenPairParser


class SequentialIngestor:
    """
    Optimized sequential ingestor for OHLCVT files.
    Uses direct PostgreSQL COPY for maximum performance.
    """

    # Batch size for COPY operations (1M records for optimal performance)
    BATCH_SIZE = 1_000_000

    # Minimum file size to process (skip empty/header-only files)
    MIN_FILE_SIZE = 100  # bytes

    def __init__(self, database: str = "questdb", data_dir: Optional[str] = None):
        """Initialize the sequential ingestor."""
        self.database = database
        self.data_dir = data_dir  # For testing with custom data directory
        self.asset_cache: Dict[str, Asset] = {}
        self.staging_tables_created = False
        self.has_unique_constraints = None  # Will be checked on first use
        self.stats = {
            "files_processed": 0,
            "records_inserted": 0,
            "files_deleted": 0,
            "files_skipped": 0,
            "total_time": 0,
        }

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
        (ingested_dir / "trades").mkdir(exist_ok=True)

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
        """Get asset from cache or create if needed."""
        if ticker not in self.asset_cache:
            # Use KrakenAssetCreator to get or create the asset
            asset_creator = KrakenAssetCreator(database=self.database)

            # First, ensure the asset exists by calling bulk_create_assets
            # This will create it if it doesn't exist
            asset_creator.bulk_create_assets([pair_name])

            # Now get the asset using get_or_create_asset method
            # which will retrieve it from the database or cache
            asset = asset_creator.get_or_create_asset(ticker)

            # Cache the asset for future use
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

    def _check_unique_constraints(self):
        """Check if the required unique constraints exist in the database."""
        if self.has_unique_constraints is not None:
            return self.has_unique_constraints

        with connections[self.database].cursor() as cursor:
            # Check if the unique constraint exists on assetprice table
            cursor.execute("""
                SELECT COUNT(*) FROM pg_constraint
                WHERE conrelid = 'feefifofunds_assetprice'::regclass
                AND contype = 'u'
                AND array_length(conkey, 1) = 5
            """)
            result = cursor.fetchone()
            self.has_unique_constraints = result[0] > 0

        return self.has_unique_constraints

    def _create_staging_tables(self):
        """Create staging tables once for the entire session."""
        if self.staging_tables_created:
            return

        with connections[self.database].cursor() as cursor:
            # Create persistent temporary tables for the session
            cursor.execute("""
                CREATE TEMP TABLE IF NOT EXISTS staging_assetprice (
                    asset_id INTEGER,
                    time TIMESTAMPTZ,
                    open NUMERIC(20,8),
                    high NUMERIC(20,8),
                    low NUMERIC(20,8),
                    close NUMERIC(20,8),
                    volume NUMERIC(20,2),
                    interval_minutes SMALLINT,
                    trade_count INTEGER,
                    quote_currency VARCHAR(10),
                    source VARCHAR(50),
                    created_at TIMESTAMPTZ
                )
            """)

            cursor.execute("""
                CREATE TEMP TABLE IF NOT EXISTS staging_trade (
                    asset_id INTEGER,
                    time TIMESTAMPTZ,
                    price NUMERIC(20,8),
                    volume NUMERIC(20,8),
                    quote_currency VARCHAR(10),
                    source VARCHAR(50),
                    created_at TIMESTAMPTZ
                )
            """)

        self.staging_tables_created = True

    def process_ohlcv_file(
        self,
        filepath: Path,
        asset: Asset,
        interval_minutes: int,
        quote_currency: str,
        progress_callback=None,
    ) -> int:
        """
        Process a single OHLCV file using optimized COPY.

        Returns:
            Number of records inserted
        """
        records_inserted = 0
        batch_buffer = StringIO()
        batch_count = 0

        with open(filepath, "r") as csvfile:
            # Skip header if present
            first_line = csvfile.readline()
            if self._is_header_line(first_line):
                # First line is header, already consumed
                pass
            else:
                # First line is data, seek back
                csvfile.seek(0)

            reader = csv.reader(csvfile)

            for row_num, row in enumerate(reader, 1):
                if len(row) < 6:
                    continue  # Skip invalid rows

                # Parse row: timestamp,open,high,low,close,volume,trade_count
                # Handle both int and float timestamps
                timestamp = datetime.fromtimestamp(float(row[0]), tz=timezone.utc)
                open_price = Decimal(row[1])
                high_price = Decimal(row[2])
                low_price = Decimal(row[3])
                close_price = Decimal(row[4])
                volume = Decimal(row[5]) if row[5] else None
                trade_count = int(row[6]) if len(row) > 6 and row[6] else None

                # Write to buffer in TSV format for COPY
                batch_buffer.write(
                    f"{asset.id}\t{timestamp.isoformat()}\t{open_price}\t{high_price}\t"
                    f"{low_price}\t{close_price}\t{volume or '\\N'}\t"
                    f"{interval_minutes}\t{trade_count or '\\N'}\t"
                    f"{quote_currency}\tkraken\t{datetime.now(timezone.utc).isoformat()}\n"
                )
                batch_count += 1

                # Execute COPY when batch is full
                if batch_count >= self.BATCH_SIZE:
                    records_inserted += self._execute_copy_batch(batch_buffer, "assetprice")
                    batch_buffer = StringIO()
                    batch_count = 0

                    if progress_callback and row_num % 10000 == 0:
                        progress_callback(row_num)

            # Process remaining records
            if batch_count > 0:
                records_inserted += self._execute_copy_batch(batch_buffer, "assetprice")

        return records_inserted

    def process_trade_file(self, filepath: Path, asset: Asset, quote_currency: str, progress_callback=None) -> int:
        """
        Process a single trade file using optimized COPY.

        Returns:
            Number of records inserted
        """
        records_inserted = 0
        batch_buffer = StringIO()
        batch_count = 0

        with open(filepath, "r") as csvfile:
            # Skip header if present
            first_line = csvfile.readline()
            if self._is_header_line(first_line):
                # First line is header, already consumed
                pass
            else:
                # First line is data, seek back
                csvfile.seek(0)

            reader = csv.reader(csvfile)

            for row_num, row in enumerate(reader, 1):
                if len(row) < 3:
                    continue  # Skip invalid rows

                # Parse row: timestamp,price,volume
                # Handle both int and float timestamps
                timestamp = datetime.fromtimestamp(float(row[0]), tz=timezone.utc)
                price = Decimal(row[1])
                volume = Decimal(row[2])

                # Write to buffer in TSV format for COPY
                batch_buffer.write(
                    f"{asset.id}\t{timestamp.isoformat()}\t{price}\t{volume}\t"
                    f"{quote_currency}\tkraken\t{datetime.now(timezone.utc).isoformat()}\n"
                )
                batch_count += 1

                # Execute COPY when batch is full
                if batch_count >= self.BATCH_SIZE:
                    records_inserted += self._execute_copy_batch(batch_buffer, "trade")
                    batch_buffer = StringIO()
                    batch_count = 0

                    if progress_callback and row_num % 10000 == 0:
                        progress_callback(row_num)

            # Process remaining records
            if batch_count > 0:
                records_inserted += self._execute_copy_batch(batch_buffer, "trade")

        return records_inserted

    def _execute_copy_batch(self, buffer: StringIO, table_type: str) -> int:
        """
        Execute PostgreSQL COPY for a batch of records.

        Args:
            buffer: StringIO containing TSV data
            table_type: 'assetprice' or 'trade'

        Returns:
            Number of records inserted
        """
        # Ensure staging tables exist
        self._create_staging_tables()

        buffer.seek(0)

        # Get the database connection
        db_conn = connections[self.database]

        with db_conn.cursor() as cursor:
            # Clear staging table first
            cursor.execute(f"TRUNCATE staging_{table_type}")

            # Set performance options for this transaction
            cursor.execute("SET LOCAL synchronous_commit = OFF")
            cursor.execute("SET LOCAL work_mem = '1GB'")

            # Check if unique constraints exist
            has_constraints = self._check_unique_constraints()

            # Prepare SQL statements based on table type
            if table_type == "assetprice":
                table_name = "staging_assetprice"
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
                copy_sql = f"""
                    COPY {table_name} ({', '.join(columns)})
                    FROM STDIN WITH (FORMAT text, NULL '\\N')
                """

                if has_constraints:
                    # Use fast ON CONFLICT if constraints exist
                    insert_sql = """
                        INSERT INTO feefifofunds_assetprice (
                            asset_id, time, open, high, low, close, volume,
                            interval_minutes, trade_count, quote_currency, source, created_at
                        )
                        SELECT * FROM staging_assetprice
                        ON CONFLICT (asset_id, time, source, interval_minutes, quote_currency)
                        DO NOTHING
                    """
                else:
                    # Use WHERE NOT EXISTS as fallback (slower but works without constraints)
                    insert_sql = """
                        INSERT INTO feefifofunds_assetprice (
                            asset_id, time, open, high, low, close, volume,
                            interval_minutes, trade_count, quote_currency, source, created_at
                        )
                        SELECT s.* FROM staging_assetprice s
                        WHERE NOT EXISTS (
                            SELECT 1 FROM feefifofunds_assetprice p
                            WHERE p.asset_id = s.asset_id
                            AND p.time = s.time
                            AND p.source = s.source
                            AND p.interval_minutes = s.interval_minutes
                            AND p.quote_currency = s.quote_currency
                        )
                    """
            else:  # trade
                table_name = "staging_trade"
                columns = ("asset_id", "time", "price", "volume", "quote_currency", "source", "created_at")
                copy_sql = f"""
                    COPY {table_name} ({', '.join(columns)})
                    FROM STDIN WITH (FORMAT text, NULL '\\N')
                """

                if has_constraints:
                    # Use fast ON CONFLICT if constraints exist
                    insert_sql = """
                        INSERT INTO feefifofunds_trade (
                            asset_id, time, price, volume, quote_currency, source, created_at
                        )
                        SELECT * FROM staging_trade
                        ON CONFLICT (asset_id, time, source, quote_currency)
                        DO NOTHING
                    """
                else:
                    # Use WHERE NOT EXISTS as fallback (slower but works without constraints)
                    insert_sql = """
                        INSERT INTO feefifofunds_trade (
                            asset_id, time, price, volume, quote_currency, source, created_at
                        )
                        SELECT s.* FROM staging_trade s
                        WHERE NOT EXISTS (
                            SELECT 1 FROM feefifofunds_trade t
                            WHERE t.asset_id = s.asset_id
                            AND t.time = s.time
                            AND t.source = s.source
                            AND t.quote_currency = s.quote_currency
                        )
                    """

            # Execute COPY operation
            # Get the raw database connection to handle COPY
            raw_conn = db_conn.connection

            # Create a cursor from the raw connection for COPY operation
            with raw_conn.cursor() as copy_cursor:
                # Check which COPY method is available (psycopg3 vs psycopg2)
                if hasattr(copy_cursor, "copy"):
                    # psycopg3: use copy() context manager
                    with copy_cursor.copy(copy_sql) as copy:
                        # Read the buffer content and write to COPY
                        data = buffer.read()
                        copy.write(data.encode("utf-8") if isinstance(data, str) else data)
                elif hasattr(copy_cursor, "copy_expert"):
                    # psycopg2: use copy_expert
                    copy_cursor.copy_expert(copy_sql, buffer)
                else:
                    # Fallback: use copy_from (psycopg2 alternative)
                    copy_cursor.copy_from(buffer, table_name, columns=columns, sep="\t", null="\\N")

            # Merge from staging to main table
            cursor.execute(insert_sql)

            # Get actual insert count
            inserted = cursor.rowcount

            return inserted

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
        """Run database optimizations before bulk ingestion."""
        with connections[self.database].cursor() as cursor:
            # Increase work memory for this session
            cursor.execute("SET work_mem = '1GB'")
            cursor.execute("SET maintenance_work_mem = '2GB'")

            # Temporarily disable autovacuum (will be re-enabled after)
            cursor.execute("ALTER TABLE feefifofunds_assetprice SET (autovacuum_enabled = false)")
            cursor.execute("ALTER TABLE feefifofunds_trade SET (autovacuum_enabled = false)")

    def restore_database(self):
        """Restore database settings after bulk ingestion."""
        # First, re-enable autovacuum
        with connections[self.database].cursor() as cursor:
            cursor.execute("ALTER TABLE feefifofunds_assetprice SET (autovacuum_enabled = true)")
            cursor.execute("ALTER TABLE feefifofunds_trade SET (autovacuum_enabled = true)")

            # Run ANALYZE to update statistics
            cursor.execute("ANALYZE feefifofunds_assetprice")
            cursor.execute("ANALYZE feefifofunds_trade")

        # VACUUM must be run outside of transaction
        # Close any existing connections and get a new one with autocommit
        connection = connections[self.database]
        connection.ensure_connection()

        # Store the original autocommit setting
        old_autocommit = connection.autocommit
        try:
            # Enable autocommit for VACUUM
            connection.set_autocommit(True)
            with connection.cursor() as cursor:
                cursor.execute("VACUUM ANALYZE feefifofunds_assetprice")
                cursor.execute("VACUUM ANALYZE feefifofunds_trade")
        finally:
            # Restore original autocommit setting
            connection.set_autocommit(old_autocommit)
