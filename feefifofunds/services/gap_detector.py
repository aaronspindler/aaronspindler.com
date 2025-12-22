import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List

from django.db import transaction

from feefifofunds.models import Asset, DataCoverageRange, GapRecord, IngestionJob

logger = logging.getLogger(__name__)


@dataclass
class Gap:
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
    total_gaps: int
    fillable_gaps: List[Gap]
    unfillable_gaps: List[Gap]

    @property
    def fillable_count(self) -> int:
        return len(self.fillable_gaps)

    @property
    def unfillable_count(self) -> int:
        return len(self.unfillable_gaps)


class IntegratedGapDetector:
    API_CANDLE_LIMIT = 720  # Kraken API maximum

    def __init__(self):
        pass

    def detect_gaps_for_job(self, job: IngestionJob) -> GapDetectionResult:
        logger.info(f"Detecting gaps for job {job.job_id}")

        fillable_gaps = []
        unfillable_gaps = []

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
        logger.debug(
            f"Detecting gaps for {asset.ticker} {interval_minutes}min: {expected_start.date()} to {expected_end.date()}"
        )

        coverage_ranges = list(
            DataCoverageRange.objects.filter(asset=asset, interval_minutes=interval_minutes).order_by("start_date")
        )

        gaps = []
        current_date = expected_start

        for coverage in coverage_ranges:
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

            current_date = max(current_date, coverage.end_date)

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
        now = datetime.now()

        # Calculate missing candles
        gap_minutes = (end - start).total_seconds() / 60
        missing_candles = int(gap_minutes / interval_minutes)

        # Calculate API fillability
        is_api_fillable, overflow_candles, candles_from_today = GapRecord.calculate_api_fillability(
            interval_minutes=interval_minutes, gap_start=start, now=now
        )

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
        with transaction.atomic():
            existing = GapRecord.objects.filter(
                asset=gap.asset,
                interval_minutes=gap.interval_minutes,
                gap_start=gap.start_date,
                gap_end=gap.end_date,
            ).first()

            if existing:
                logger.debug(f"Gap already exists: {gap.asset.ticker} {gap.interval_minutes}min")
                return existing

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
        query = GapRecord.objects.filter(
            is_api_fillable=True, status__in=[GapRecord.Status.DETECTED, GapRecord.Status.FAILED]
        )

        if tier:
            query = query.filter(asset__tier=tier)

        if interval_minutes:
            query = query.filter(interval_minutes=interval_minutes)

        return list(query.order_by("-detected_at")[:limit])

    def get_unfillable_gaps(self, tier: str | None = None, interval_minutes: int | None = None) -> List[GapRecord]:
        query = GapRecord.objects.filter(status=GapRecord.Status.UNFILLABLE)

        if tier:
            query = query.filter(asset__tier=tier)

        if interval_minutes:
            query = query.filter(interval_minutes=interval_minutes)

        return list(query.order_by("-detected_at"))

    def export_csv_download_list(self, gaps: List[GapRecord], output_file: str) -> dict:
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
        query = GapRecord.objects.all()

        if tier:
            query = query.filter(asset__tier=tier)

        total_gaps = query.count()
        fillable = query.filter(is_api_fillable=True).count()
        unfillable = query.filter(is_api_fillable=False).count()

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
