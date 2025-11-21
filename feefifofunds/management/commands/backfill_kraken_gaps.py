"""
Detects and backfills gaps in asset price data using the Kraken REST API.

Identifies both missing days and missing intervals within days, classifies gaps
based on Kraken's 720-candle API limitation, and provides options for interactive
backfilling.
"""

import csv
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.db import connections
from questdb.ingress import Sender, TimestampNanos

from feefifofunds.models import Asset
from feefifofunds.services.data_sources import KrakenDataSource


@dataclass
class Gap:
    """Represents a gap in asset price data."""

    asset: Asset
    interval_minutes: int
    quote_currency: str
    source: str
    start_date: datetime
    end_date: datetime
    missing_candles: int
    candles_from_today: int
    is_api_fillable: bool
    overflow_candles: int


class GapClassifier:
    """Classifies gaps based on Kraken's 720-candle API limitation."""

    MAX_CANDLES = 720

    @classmethod
    def calculate_candles_from_today(cls, date_or_datetime: datetime, interval_minutes: int) -> int:
        """
        Calculate how many candles exist between a date and today.

        Examples:
        - interval=1440, date=30 days ago → 30 candles
        - interval=60, date=10 days ago → 240 candles (10*24)
        - interval=5, date=1 day ago → 288 candles (24*60/5)
        """
        today = datetime.now(timezone.utc)
        time_diff = today - date_or_datetime
        minutes_diff = time_diff.total_seconds() / 60
        candles = int(minutes_diff / interval_minutes)
        return candles

    @classmethod
    def classify_gap(cls, gap_end_date: datetime, interval_minutes: int) -> Tuple[bool, int, int]:
        """
        Check if gap is within Kraken's 720-candle API limit.

        Returns:
            (is_fillable, candles_from_today, overflow)
        """
        candles = cls.calculate_candles_from_today(gap_end_date, interval_minutes)
        is_fillable = candles <= cls.MAX_CANDLES
        overflow = max(0, candles - cls.MAX_CANDLES)
        return is_fillable, candles, overflow


class GapDetector:
    """Detects gaps in QuestDB assetprice data."""

    def __init__(self, tier_filter: Optional[str] = None):
        self.tier_filter = tier_filter

    def get_assets_to_check(self) -> List[Asset]:
        """Get list of assets to check based on tier filter."""
        queryset = Asset.objects.filter(active=True, category=Asset.Category.CRYPTO)
        if self.tier_filter and self.tier_filter != "ALL":
            queryset = queryset.filter(tier=self.tier_filter)
        return list(queryset)

    def get_asset_interval_combinations(self, asset_id: int) -> List[Tuple[int, str, str]]:
        """Get all (interval_minutes, quote_currency, source) tuples for an asset from Kraken sources."""
        query = """
        SELECT DISTINCT interval_minutes, quote_currency, source
        FROM assetprice
        WHERE asset_id = %s AND source IN ('kraken', 'kraken_api')
        ORDER BY interval_minutes, quote_currency, source
        """
        with connections["questdb"].cursor() as cursor:
            cursor.execute(query, [asset_id])
            return [(row[0], row[1], row[2]) for row in cursor.fetchall()]

    def get_asset_intervals(self, asset_id: int) -> List[int]:
        """Get all intervals that have data for this asset."""
        query = """
        SELECT DISTINCT interval_minutes
        FROM assetprice
        WHERE asset_id = %s
        ORDER BY interval_minutes
        """
        with connections["questdb"].cursor() as cursor:
            cursor.execute(query, [asset_id])
            return [row[0] for row in cursor.fetchall()]

    def get_date_range(
        self, asset_id: int, interval_minutes: int, quote_currency: str, source: str
    ) -> Optional[Tuple[datetime, datetime]]:
        """Get min and max timestamps for an asset/interval/quote_currency/source combination."""
        query = """
        SELECT MIN(time), MAX(time)
        FROM assetprice
        WHERE asset_id = %s AND interval_minutes = %s AND quote_currency = %s AND source = %s
        """
        with connections["questdb"].cursor() as cursor:
            cursor.execute(query, [asset_id, interval_minutes, quote_currency, source])
            result = cursor.fetchone()
            if result and result[0] and result[1]:
                return result[0], result[1]
        return None

    def get_existing_dates(self, asset_id: int, interval_minutes: int, quote_currency: str, source: str) -> set:
        """Get all distinct dates that have data for an asset/interval/quote_currency/source combination."""
        query = """
        SELECT DISTINCT DATE(time) as date
        FROM assetprice
        WHERE asset_id = %s AND interval_minutes = %s AND quote_currency = %s AND source = %s
        ORDER BY date
        """
        with connections["questdb"].cursor() as cursor:
            cursor.execute(query, [asset_id, interval_minutes, quote_currency, source])
            return {row[0] for row in cursor.fetchall()}

    def get_records_per_day(
        self, asset_id: int, interval_minutes: int, quote_currency: str, source: str
    ) -> Dict[date, int]:
        """Get record counts per day for an asset/interval/quote_currency/source combination."""
        query = """
        SELECT DATE(time) as date, COUNT(*) as count
        FROM assetprice
        WHERE asset_id = %s AND interval_minutes = %s AND quote_currency = %s AND source = %s
        GROUP BY DATE(time)
        """
        with connections["questdb"].cursor() as cursor:
            cursor.execute(query, [asset_id, interval_minutes, quote_currency, source])
            return {row[0]: row[1] for row in cursor.fetchall()}

    def calculate_expected_records_per_day(self, interval_minutes: int) -> int:
        """Calculate expected number of records per day for an interval."""
        minutes_per_day = 24 * 60
        return minutes_per_day // interval_minutes

    def detect_last_to_now_gap(
        self, asset: Asset, interval_minutes: int, quote_currency: str, source: str
    ) -> Optional[Gap]:
        """
        Detect a single gap from the last record timestamp to now.

        Returns None if no data exists for this asset/interval/quote_currency/source combination.
        """
        query = """
        SELECT MAX(time) as max_time
        FROM assetprice
        WHERE asset_id = %s AND interval_minutes = %s AND quote_currency = %s AND source = %s
        """
        with connections["questdb"].cursor() as cursor:
            cursor.execute(query, [asset.id, interval_minutes, quote_currency, source])
            result = cursor.fetchone()

            if not result or not result[0]:
                return None

            last_timestamp = result[0]
            if last_timestamp.tzinfo is None:
                last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if last_timestamp >= now:
            return None

        is_fillable, candles_from_today, overflow = GapClassifier.classify_gap(now, interval_minutes)

        expected_count = self.calculate_expected_records_per_day(interval_minutes)
        days_diff = (now - last_timestamp).days
        missing_candles = days_diff * expected_count

        return Gap(
            asset=asset,
            interval_minutes=interval_minutes,
            quote_currency=quote_currency,
            source=source,
            start_date=last_timestamp,
            end_date=now,
            missing_candles=missing_candles,
            candles_from_today=candles_from_today,
            is_api_fillable=is_fillable,
            overflow_candles=overflow,
        )

    def detect_gaps(self, asset: Asset, from_last: bool = False) -> List[Gap]:
        """Detect all gaps for an asset, separately for each (interval_minutes, quote_currency, source) combination."""
        gaps = []
        combinations = self.get_asset_interval_combinations(asset.id)

        if from_last:
            for interval_minutes, quote_currency, source in combinations:
                gap = self.detect_last_to_now_gap(asset, interval_minutes, quote_currency, source)
                if gap:
                    gaps.append(gap)
            return gaps

        for interval_minutes, quote_currency, source in combinations:
            date_range = self.get_date_range(asset.id, interval_minutes, quote_currency, source)
            if not date_range:
                continue

            min_date, max_date = date_range
            existing_dates = self.get_existing_dates(asset.id, interval_minutes, quote_currency, source)
            records_per_day = self.get_records_per_day(asset.id, interval_minutes, quote_currency, source)
            expected_count = self.calculate_expected_records_per_day(interval_minutes)

            current_date = min_date.date()
            max_date_only = max_date.date()
            gap_start = None

            while current_date <= max_date_only:
                is_missing_day = current_date not in existing_dates
                has_incomplete_data = current_date in records_per_day and records_per_day[current_date] < expected_count

                if is_missing_day or has_incomplete_data:
                    if gap_start is None:
                        gap_start = current_date
                elif gap_start is not None:
                    gap_end = current_date
                    gap_end_dt = datetime.combine(gap_end, datetime.min.time()).replace(tzinfo=timezone.utc)

                    is_fillable, candles_from_today, overflow = GapClassifier.classify_gap(gap_end_dt, interval_minutes)

                    days_diff = (gap_end - gap_start).days
                    missing_candles = days_diff * expected_count

                    gaps.append(
                        Gap(
                            asset=asset,
                            interval_minutes=interval_minutes,
                            quote_currency=quote_currency,
                            source=source,
                            start_date=datetime.combine(gap_start, datetime.min.time()).replace(tzinfo=timezone.utc),
                            end_date=gap_end_dt,
                            missing_candles=missing_candles,
                            candles_from_today=candles_from_today,
                            is_api_fillable=is_fillable,
                            overflow_candles=overflow,
                        )
                    )
                    gap_start = None

                current_date = date.fromordinal(current_date.toordinal() + 1)

            if gap_start is not None:
                gap_end_dt = datetime.combine(max_date_only, datetime.min.time()).replace(tzinfo=timezone.utc)
                is_fillable, candles_from_today, overflow = GapClassifier.classify_gap(gap_end_dt, interval_minutes)

                days_diff = (max_date_only - gap_start).days
                missing_candles = days_diff * expected_count

                gaps.append(
                    Gap(
                        asset=asset,
                        interval_minutes=interval_minutes,
                        quote_currency=quote_currency,
                        source=source,
                        start_date=datetime.combine(gap_start, datetime.min.time()).replace(tzinfo=timezone.utc),
                        end_date=gap_end_dt,
                        missing_candles=missing_candles,
                        candles_from_today=candles_from_today,
                        is_api_fillable=is_fillable,
                        overflow_candles=overflow,
                    )
                )

        return gaps


class GapBackfiller:
    """Backfills gaps using Kraken API and QuestDB ILP."""

    KRAKEN_SUPPORTED_INTERVALS = {1, 5, 15, 30, 60, 240, 1440, 10080, 21600}

    def __init__(self, stdout):
        self.kraken = KrakenDataSource()
        self.stdout = stdout
        self.ilp_host, self.ilp_port = self._get_ilp_connection()
        self.ilp_conf = f"tcp::addr={self.ilp_host}:{self.ilp_port};"

    def _get_ilp_connection(self) -> Tuple[str, int]:
        """Extract ILP connection details from QUESTDB_URL environment variable."""
        questdb_url = os.environ.get("QUESTDB_URL", "")
        if questdb_url:
            parsed = urlparse(questdb_url)
            host = parsed.hostname or "localhost"
            return host, 9009
        return "localhost", 9009

    def backfill_gap(self, gap: Gap) -> Tuple[bool, int, Optional[str]]:
        """
        Backfill a single gap using Kraken API.

        Returns:
            (success, records_inserted, error_message)
        """
        try:
            base_ticker = self._get_kraken_base_ticker(gap.asset.ticker)
            kraken_pair = self._build_kraken_pair(base_ticker, gap.quote_currency)

            price_data = self.kraken.fetch_historical_prices(
                pair=kraken_pair,
                start_date=gap.start_date.date(),
                end_date=gap.end_date.date(),
                interval_minutes=gap.interval_minutes,
            )

            if not price_data:
                return False, 0, "No data returned from Kraken"

            records_inserted = self._write_to_questdb(
                gap.asset, price_data, gap.quote_currency, gap.interval_minutes, gap.source
            )
            return True, records_inserted, None

        except Exception as e:
            return False, 0, str(e)

    def _get_kraken_base_ticker(self, ticker: str) -> str:
        """Convert ticker to Kraken base ticker format."""
        ticker_to_kraken = {
            "BTC": "XBT",
            "DOGE": "XDG",
        }
        return ticker_to_kraken.get(ticker, ticker)

    def _build_kraken_pair(self, base_ticker: str, quote_currency: str) -> str:
        """Build Kraken pair string from base ticker and quote currency."""
        # Reverse mapping from normalized quote currency to Kraken format
        # Kraken uses Z-prefixed versions for fiat currencies (ZUSD, ZEUR, etc.)
        normalized_to_kraken = {
            "USD": "ZUSD",
            "EUR": "ZEUR",
            "GBP": "ZGBP",
            "JPY": "ZJPY",
            "CAD": "ZCAD",
            "CHF": "ZCHF",
            "AUD": "ZAUD",
            "AED": "ZAED",
        }
        kraken_quote = normalized_to_kraken.get(quote_currency, quote_currency)
        return base_ticker + kraken_quote

    def _write_to_questdb(
        self, asset: Asset, price_data: List[dict], quote_currency: str, interval_minutes: int, source: str
    ) -> int:
        """Write price data to QuestDB using ILP."""
        records_inserted = 0

        try:
            with Sender.from_conf(self.ilp_conf) as sender:
                for data in price_data:
                    sender.row(
                        "assetprice",
                        symbols={"quote_currency": quote_currency, "source": source},
                        columns={
                            "asset_id": asset.id,
                            "open": float(data["open"]),
                            "high": float(data["high"]),
                            "low": float(data["low"]),
                            "close": float(data["close"]),
                            "volume": float(data["volume"]),
                            "interval_minutes": interval_minutes,
                            "trade_count": data.get("trade_count", 0),
                        },
                        at=TimestampNanos.from_datetime(data["timestamp"]),
                    )
                    records_inserted += 1

        except Exception:
            raise

        return records_inserted


class Command(BaseCommand):
    """
    Detect and backfill gaps in Kraken asset price data.

    Identifies missing days and incomplete data intervals, classifies by API availability
    (720-candle limit), and provides interactive backfilling.
    """

    help = "Detect and backfill gaps in Kraken asset price data using REST API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tier",
            type=str,
            choices=["TIER1", "TIER2", "TIER3", "TIER4", "ALL"],
            help="Filter by asset tier",
        )
        parser.add_argument(
            "--asset",
            type=str,
            help="Filter by specific asset ticker",
        )
        parser.add_argument(
            "--interval",
            type=int,
            help="Filter by specific interval (e.g., 60, 1440)",
        )
        parser.add_argument(
            "--yes",
            "-y",
            action="store_true",
            help="Auto-confirm all backfills",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only detect gaps, don't backfill",
        )
        parser.add_argument(
            "--show-unfillable-only",
            action="store_true",
            help="Only show gaps beyond 720-candle limit",
        )
        parser.add_argument(
            "--export-unfillable",
            type=str,
            help="Export unfillable gaps to CSV file",
        )
        parser.add_argument(
            "--from-last",
            action="store_true",
            help="Only fill gaps from the last record timestamp to now for each asset/interval",
        )

    def handle(self, *args, **options):
        tier_filter = options.get("tier")
        asset_filter = options.get("asset")
        interval_filter = options.get("interval")
        auto_confirm = options["yes"]
        dry_run = options["dry_run"]
        show_unfillable_only = options["show_unfillable_only"]
        export_file = options.get("export_unfillable")
        from_last = options["from_last"]

        self.stdout.write("═" * 60)
        self.stdout.write(self.style.SUCCESS("Kraken Gap Detection Report"))
        self.stdout.write("═" * 60)
        self.stdout.write("")

        detector = GapDetector(tier_filter=tier_filter)
        assets = detector.get_assets_to_check()

        if asset_filter:
            assets = [a for a in assets if a.ticker.upper() == asset_filter.upper()]

        if not assets:
            self.stdout.write(self.style.WARNING("No assets found matching filters"))
            return

        mode_text = "FROM-LAST mode (last timestamp → now)" if from_last else "all gaps"
        self.stdout.write(f"Scanning {len(assets)} assets for {mode_text}...")
        self.stdout.write("")

        all_gaps = []
        for asset in assets:
            gaps = detector.detect_gaps(asset, from_last=from_last)
            if interval_filter:
                gaps = [g for g in gaps if g.interval_minutes == interval_filter]
            all_gaps.extend(gaps)

        if not all_gaps:
            self.stdout.write(self.style.SUCCESS("✓ No gaps found!"))
            return

        fillable_gaps = [g for g in all_gaps if g.is_api_fillable]
        unfillable_gaps = [g for g in all_gaps if not g.is_api_fillable]

        supported_gaps = [g for g in fillable_gaps if g.interval_minutes in GapBackfiller.KRAKEN_SUPPORTED_INTERVALS]
        unsupported_interval_gaps = [
            g for g in fillable_gaps if g.interval_minutes not in GapBackfiller.KRAKEN_SUPPORTED_INTERVALS
        ]

        if unsupported_interval_gaps:
            self._display_unsupported_intervals(unsupported_interval_gaps)

        if not show_unfillable_only and supported_gaps:
            self._display_fillable_gaps(supported_gaps)

        if unfillable_gaps:
            self._display_unfillable_gaps(unfillable_gaps)

        if export_file:
            self._export_unfillable_gaps(unfillable_gaps, export_file)

        if dry_run or not supported_gaps:
            return

        if show_unfillable_only:
            return

        if not auto_confirm:
            response = input(f"\nProceed with backfilling {len(supported_gaps)} Kraken-supported gaps? [y/N]: ")
            if response.lower() != "y":
                self.stdout.write("Backfill cancelled")
                return

        self._backfill_gaps(supported_gaps)

    def _display_unsupported_intervals(self, gaps: List[Gap]):
        """Display gaps with intervals not supported by Kraken."""
        self.stdout.write("─" * 60)
        self.stdout.write(self.style.WARNING("⚠️  UNSUPPORTED INTERVALS (Kraken doesn't support these intervals)"))
        self.stdout.write("─" * 60)
        self.stdout.write("")

        by_asset = defaultdict(list)
        for gap in gaps:
            by_asset[gap.asset.ticker].append(gap)

        for ticker in sorted(by_asset.keys()):
            asset_gaps = by_asset[ticker]
            tier = asset_gaps[0].asset.tier
            self.stdout.write(f"{ticker} ({tier}):")
            for gap in asset_gaps:
                days = (gap.end_date - gap.start_date).days
                self.stdout.write(
                    f"  ⚠ {gap.start_date.date()} → {gap.end_date.date()} "
                    f"({days} days, interval: {gap.interval_minutes} min, {gap.quote_currency})"
                )
                self.stdout.write(
                    f"    └─ Kraken supports: {', '.join(str(i) for i in sorted(GapBackfiller.KRAKEN_SUPPORTED_INTERVALS))}"
                )
            self.stdout.write("")

        self.stdout.write(f"Summary: {len(gaps)} gaps with unsupported intervals (will be skipped)")
        self.stdout.write("")

    def _display_fillable_gaps(self, gaps: List[Gap]):
        """Display API-fillable gaps."""
        self.stdout.write("─" * 60)
        self.stdout.write(self.style.SUCCESS("📊 API-FILLABLE GAPS (within 720-candle limit)"))
        self.stdout.write("─" * 60)
        self.stdout.write("")

        by_asset = defaultdict(list)
        for gap in gaps:
            by_asset[gap.asset.ticker].append(gap)

        for ticker in sorted(by_asset.keys()):
            asset_gaps = by_asset[ticker]
            tier = asset_gaps[0].asset.tier
            self.stdout.write(f"{ticker} ({tier}):")
            for gap in asset_gaps:
                days = (gap.end_date - gap.start_date).days
                self.stdout.write(
                    f"  ✓ {gap.start_date.date()} → {gap.end_date.date()} "
                    f"({days} days, ~{gap.missing_candles} candles, interval: {gap.interval_minutes} min, {gap.quote_currency})"
                )
                self.stdout.write(
                    f"    └─ {gap.candles_from_today} candles from today (limit: {GapClassifier.MAX_CANDLES}) ✓"
                )
            self.stdout.write("")

        total_candles = sum(g.missing_candles for g in gaps)
        self.stdout.write(f"Summary: {len(gaps)} fillable gaps, ~{total_candles} total candles to fetch")
        self.stdout.write("")

    def _display_unfillable_gaps(self, gaps: List[Gap]):
        """Display gaps beyond API limit."""
        self.stdout.write("─" * 60)
        self.stdout.write(self.style.ERROR("❌ UNFILLABLE GAPS (beyond 720-candle limit)"))
        self.stdout.write("─" * 60)
        self.stdout.write("")

        by_asset = defaultdict(list)
        for gap in gaps:
            by_asset[gap.asset.ticker].append(gap)

        for ticker in sorted(by_asset.keys()):
            asset_gaps = by_asset[ticker]
            tier = asset_gaps[0].asset.tier
            self.stdout.write(f"{ticker} ({tier}):")
            for gap in asset_gaps:
                days = (gap.end_date - gap.start_date).days
                overflow_days = gap.overflow_candles * gap.interval_minutes // 1440
                self.stdout.write(
                    f"  ✗ {gap.start_date.date()} → {gap.end_date.date()} "
                    f"({days} days, ~{gap.missing_candles} candles, interval: {gap.interval_minutes} min, {gap.quote_currency})"
                )
                self.stdout.write(
                    f"    └─ {gap.candles_from_today} candles from today (limit: {GapClassifier.MAX_CANDLES}) ✗"
                )
                self.stdout.write(f"    └─ TOO OLD by {gap.overflow_candles} candles (~{overflow_days} days)")
                self.stdout.write(
                    f"    → ACTION: Download CSV from Kraken for {gap.start_date.date()} to {gap.end_date.date()}"
                )
            self.stdout.write("")

        self.stdout.write(f"Summary: {len(gaps)} unfillable gaps")
        self.stdout.write("  → Requires CSV export or alternative data source")
        self.stdout.write("  → Kraken CSV export: https://www.kraken.com/features/api#ohlc-data")
        self.stdout.write("")

    def _export_unfillable_gaps(self, gaps: List[Gap], filepath: str):
        """Export unfillable gaps to CSV."""
        with open(filepath, "w", encoding="utf-8", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "asset_ticker",
                    "tier",
                    "interval_minutes",
                    "quote_currency",
                    "source",
                    "gap_start",
                    "gap_end",
                    "missing_candles",
                    "candles_from_today",
                    "overflow_candles",
                ]
            )
            for gap in gaps:
                writer.writerow(
                    [
                        gap.asset.ticker,
                        gap.asset.tier,
                        gap.interval_minutes,
                        gap.quote_currency,
                        gap.source,
                        gap.start_date.date(),
                        gap.end_date.date(),
                        gap.missing_candles,
                        gap.candles_from_today,
                        gap.overflow_candles,
                    ]
                )
        self.stdout.write(self.style.SUCCESS(f"Exported {len(gaps)} unfillable gaps to {filepath}"))

    def _backfill_gaps(self, gaps: List[Gap]):
        """Backfill all fillable gaps."""
        self.stdout.write("═" * 60)
        self.stdout.write(self.style.SUCCESS("Backfilling Gaps"))
        self.stdout.write("═" * 60)
        self.stdout.write("")

        backfiller = GapBackfiller(self.stdout)

        success_count = 0
        failure_count = 0
        total_records = 0

        for i, gap in enumerate(gaps, 1):
            self.stdout.write(
                f"\n[{i}/{len(gaps)}] Backfilling {gap.asset.ticker} "
                f"({gap.start_date.date()} → {gap.end_date.date()}, {gap.interval_minutes} min, {gap.quote_currency})..."
            )

            success, records, error = backfiller.backfill_gap(gap)

            if success:
                success_count += 1
                total_records += records
                self.stdout.write(self.style.SUCCESS(f"  ✓ Inserted {records} records"))
            else:
                failure_count += 1
                self.stdout.write(self.style.ERROR(f"  ✗ Failed: {error}"))

        self.stdout.write("")
        self.stdout.write("═" * 60)
        self.stdout.write(self.style.SUCCESS("Backfill Complete"))
        self.stdout.write("═" * 60)
        self.stdout.write(f"Success: {success_count}")
        self.stdout.write(f"Failures: {failure_count}")
        self.stdout.write(f"Total records inserted: {total_records}")
