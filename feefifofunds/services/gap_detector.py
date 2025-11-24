"""
Integrated Gap Detector for identifying missing data ranges.

This service detects gaps by comparing expected coverage (based on start/end dates)
against actual coverage (DataCoverageRange), and classifies gaps by API fillability.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List

from django.db import transaction

from feefifofunds.models import Asset, DataCoverageRange, GapRecord, IngestionJob

logger = logging.getLogger(__name__)


@dataclass
class Gap:
    """Represents a detected data gap."""

    asset: Asset
    interval_minutes: int
    start_date: datetime
    end_date: datetime
    missing_candles: int
    is_api_fillable: bool
    overflow_candles: int
    candles_from_today: int
    required_csv_file: str | None = None


@dataclass
class GapDetectionResult:
    """Results from gap detection."""

    total_gaps: int
    fillable_gaps: List[Gap]
    unfillable_gaps: List[Gap]

    @property
    def fillable_count(self) -> int:
        """Count of API-fillable gaps."""
        return len(self.fillable_gaps)

    @property
    def unfillable_count(self) -> int:
        """Count of unfillable gaps (require CSV)."""
        return len(self.unfillable_gaps)


class IntegratedGapDetector:
    """
    Detect gaps by comparing expected vs actual data coverage.

    This service integrates with DataCoverageRange to efficiently detect
    missing date ranges without scanning all records in QuestDB.
    """

    API_CANDLE_LIMIT = 720  # Kraken API maximum

    def __init__(self):
        """Initialize gap detector."""
        pass

    def detect_gaps_for_job(self, job: IngestionJob) -> GapDetectionResult:
        """
        Detect all gaps for an ingestion job.

        Args:
            job: IngestionJob to detect gaps for

        Returns:
            GapDetectionResult with fillable and unfillable gaps
        """
        logger.info(f"Detecting gaps for job {job.job_id}")

        fillable_gaps = []
        unfillable_gaps = []

        # Get assets for tier
        if job.tier == "ALL":
            assets = Asset.objects.filter(category=Asset.Category.CRYPTO, active=True)
        else:
            assets = Asset.objects.filter(category=Asset.Category.CRYPTO, tier=job.tier, active=True)

        logger.info(f"Checking {assets.count()} assets for gaps")

        for asset in assets:
            for interval_minutes in job.intervals:
                gaps = self.detect_gaps_for_asset(
                    asset=asset,
                    interval_minutes=interval_minutes,
                    expected_start=job.start_date,
                    expected_end=job.end_date,
                )

                for gap in gaps:
                    if gap.is_api_fillable:
                        fillable_gaps.append(gap)
                    else:
                        unfillable_gaps.append(gap)

                    # Create GapRecord
                    self._create_gap_record(gap)

        logger.info(f"Gap detection complete: {len(fillable_gaps)} fillable, {len(unfillable_gaps)} unfillable")

        return GapDetectionResult(
            total_gaps=len(fillable_gaps) + len(unfillable_gaps),
            fillable_gaps=fillable_gaps,
            unfillable_gaps=unfillable_gaps,
        )

    def detect_gaps_for_asset(
        self,
        asset: Asset,
        interval_minutes: int,
        expected_start: datetime,
        expected_end: datetime,
    ) -> List[Gap]:
        """
        Detect gaps for a single asset/interval by comparing expected vs actual coverage.

        Algorithm:
        1. Query DataCoverageRange for this asset/interval
        2. Sort ranges by start_date
        3. Find missing date ranges between expected_start and expected_end
        4. Calculate API fillability for each gap
        5. Return list of Gap objects

        Args:
            asset: Asset to check
            interval_minutes: Interval in minutes
            expected_start: Expected data start date
            expected_end: Expected data end date

        Returns:
            List of detected Gap objects
        """
        logger.debug(
            f"Detecting gaps for {asset.ticker} {interval_minutes}min: {expected_start.date()} to {expected_end.date()}"
        )

        # Get coverage ranges for this asset/interval
        coverage_ranges = list(
            DataCoverageRange.objects.filter(asset=asset, interval_minutes=interval_minutes).order_by("start_date")
        )

        gaps = []
        current_date = expected_start

        for coverage in coverage_ranges:
            # Check if there's a gap before this coverage range
            if coverage.start_date > current_date:
                gap = self._create_gap(
                    asset=asset,
                    interval_minutes=interval_minutes,
                    start=current_date,
                    end=coverage.start_date,
                )
                gaps.append(gap)
                logger.debug(
                    f"  Gap found: {gap.start_date.date()} to {gap.end_date.date()} "
                    f"({gap.missing_candles} candles, fillable={gap.is_api_fillable})"
                )

            # Move current_date to end of this coverage range
            current_date = max(current_date, coverage.end_date)

        # Check for final gap (if coverage doesn't reach expected_end)
        if current_date < expected_end:
            gap = self._create_gap(asset=asset, interval_minutes=interval_minutes, start=current_date, end=expected_end)
            gaps.append(gap)
            logger.debug(
                f"  Final gap: {gap.start_date.date()} to {gap.end_date.date()} "
                f"({gap.missing_candles} candles, fillable={gap.is_api_fillable})"
            )

        if not gaps:
            logger.debug("  No gaps found")

        return gaps

    def _create_gap(self, asset: Asset, interval_minutes: int, start: datetime, end: datetime) -> Gap:
        """
        Create a Gap object with API fillability calculation.

        Args:
            asset: Asset
            interval_minutes: Interval in minutes
            start: Gap start date
            end: Gap end date

        Returns:
            Gap object
        """
        now = datetime.now()

        # Calculate missing candles
        gap_minutes = (end - start).total_seconds() / 60
        missing_candles = int(gap_minutes / interval_minutes)

        # Calculate API fillability
        is_api_fillable, overflow_candles, candles_from_today = GapRecord.calculate_api_fillability(
            interval_minutes=interval_minutes, gap_start=start, now=now
        )

        # Generate suggested CSV filename for unfillable gaps
        required_csv_file = None
        if not is_api_fillable:
            # Format: TICKER_INTERVAL_YYYY-MM.csv
            required_csv_file = f"{asset.ticker}USD_{interval_minutes}_{start.strftime('%Y-%m')}.csv"

        return Gap(
            asset=asset,
            interval_minutes=interval_minutes,
            start_date=start,
            end_date=end,
            missing_candles=missing_candles,
            is_api_fillable=is_api_fillable,
            overflow_candles=overflow_candles,
            candles_from_today=candles_from_today,
            required_csv_file=required_csv_file,
        )

    def _create_gap_record(self, gap: Gap) -> GapRecord:
        """
        Create a GapRecord entry in the database.

        Args:
            gap: Gap object to persist

        Returns:
            Created GapRecord
        """
        with transaction.atomic():
            # Check if gap already exists
            existing = GapRecord.objects.filter(
                asset=gap.asset,
                interval_minutes=gap.interval_minutes,
                gap_start=gap.start_date,
                gap_end=gap.end_date,
            ).first()

            if existing:
                logger.debug(f"Gap already exists: {gap.asset.ticker} {gap.interval_minutes}min")
                return existing

            # Create new gap record
            gap_record = GapRecord.objects.create(
                asset=gap.asset,
                interval_minutes=gap.interval_minutes,
                gap_start=gap.start_date,
                gap_end=gap.end_date,
                missing_candles=gap.missing_candles,
                is_api_fillable=gap.is_api_fillable,
                overflow_candles=gap.overflow_candles,
                candles_from_today=gap.candles_from_today,
                status=GapRecord.Status.UNFILLABLE if not gap.is_api_fillable else GapRecord.Status.DETECTED,
                required_csv_file=gap.required_csv_file,
            )

            logger.debug(f"Created GapRecord: {gap.asset.ticker} {gap.interval_minutes}min ({gap_record.status})")

            return gap_record

    def get_fillable_gaps(
        self, tier: str | None = None, interval_minutes: int | None = None, limit: int = 100
    ) -> List[GapRecord]:
        """
        Get all API-fillable gaps.

        Args:
            tier: Filter by asset tier (optional)
            interval_minutes: Filter by interval (optional)
            limit: Maximum gaps to return

        Returns:
            List of GapRecord objects
        """
        query = GapRecord.objects.filter(
            is_api_fillable=True, status__in=[GapRecord.Status.DETECTED, GapRecord.Status.FAILED]
        )

        if tier:
            query = query.filter(asset__tier=tier)

        if interval_minutes:
            query = query.filter(interval_minutes=interval_minutes)

        return list(query.order_by("-detected_at")[:limit])

    def get_unfillable_gaps(self, tier: str | None = None, interval_minutes: int | None = None) -> List[GapRecord]:
        """
        Get all unfillable gaps (require CSV download).

        Args:
            tier: Filter by asset tier (optional)
            interval_minutes: Filter by interval (optional)

        Returns:
            List of GapRecord objects
        """
        query = GapRecord.objects.filter(status=GapRecord.Status.UNFILLABLE)

        if tier:
            query = query.filter(asset__tier=tier)

        if interval_minutes:
            query = query.filter(interval_minutes=interval_minutes)

        return list(query.order_by("-detected_at"))

    def export_csv_download_list(self, gaps: List[GapRecord], output_file: str) -> dict:
        """
        Export a list of CSV files that need to be downloaded.

        Args:
            gaps: List of unfillable GapRecord objects
            output_file: Path to output CSV file

        Returns:
            Dictionary with export statistics
        """
        import csv

        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Ticker",
                    "Tier",
                    "Interval (min)",
                    "Gap Start",
                    "Gap End",
                    "Missing Candles",
                    "Suggested Filename",
                ]
            )

            for gap in gaps:
                writer.writerow(
                    [
                        gap.asset.ticker,
                        gap.asset.tier,
                        gap.interval_minutes,
                        gap.gap_start.date(),
                        gap.gap_end.date(),
                        gap.missing_candles,
                        gap.required_csv_file or f"{gap.asset.ticker}USD_{gap.interval_minutes}.csv",
                    ]
                )

        logger.info(f"Exported {len(gaps)} CSV download recommendations to {output_file}")

        return {"gaps_exported": len(gaps), "output_file": output_file}

    def get_gap_summary(self, tier: str | None = None) -> dict:
        """
        Get a summary of detected gaps.

        Args:
            tier: Filter by asset tier (optional)

        Returns:
            Dictionary with gap statistics
        """
        query = GapRecord.objects.all()

        if tier:
            query = query.filter(asset__tier=tier)

        total_gaps = query.count()
        fillable = query.filter(is_api_fillable=True).count()
        unfillable = query.filter(is_api_fillable=False).count()

        # Count by status
        status_counts = {}
        for status_choice in GapRecord.Status.choices:
            status_value = status_choice[0]
            count = query.filter(status=status_value).count()
            if count > 0:
                status_counts[status_value] = count

        return {
            "total_gaps": total_gaps,
            "fillable_gaps": fillable,
            "unfillable_gaps": unfillable,
            "by_status": status_counts,
        }
