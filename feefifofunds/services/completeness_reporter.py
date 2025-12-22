import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from feefifofunds.models import Asset, GapRecord
from feefifofunds.services.questdb_client import QuestDBClient

logger = logging.getLogger(__name__)


@dataclass
class AssetCompleteness:
    asset: Asset
    interval_minutes: int
    expected_candles: int
    actual_candles: int
    completeness_pct: float
    gaps_count: int
    fillable_gaps: int
    unfillable_gaps: int

    @property
    def is_complete(self) -> bool:
        return self.completeness_pct >= 99.9  # Allow for minor rounding

    @property
    def has_gaps(self) -> bool:
        return self.gaps_count > 0


@dataclass
class IntervalCompleteness:
    interval_minutes: int
    total_assets: int
    complete_assets: int
    partial_assets: int
    avg_completeness_pct: float
    total_gaps: int
    fillable_gaps: int
    unfillable_gaps: int
    assets: List[AssetCompleteness] = field(default_factory=list)

    @property
    def completion_rate(self) -> float:
        if self.total_assets == 0:
            return 0.0
        return (self.complete_assets / self.total_assets) * 100


@dataclass
class CompletenessReport:
    tier: str
    date_range_start: datetime
    date_range_end: datetime
    intervals: Dict[int, IntervalCompleteness] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def overall_completeness_pct(self) -> float:
        if not self.intervals:
            return 0.0
        return sum(i.avg_completeness_pct for i in self.intervals.values()) / len(self.intervals)

    @property
    def total_assets(self) -> int:
        if not self.intervals:
            return 0
        return next(iter(self.intervals.values())).total_assets

    @property
    def total_gaps(self) -> int:
        return sum(i.total_gaps for i in self.intervals.values())


class CompletenessReporter:
    def __init__(self, database: str = "questdb"):
        self.database = database
        self.questdb_client = QuestDBClient(database=database)

    def generate_report(
        self,
        tier: str,
        intervals: List[int],
        start_date: datetime,
        end_date: datetime,
    ) -> CompletenessReport:
        logger.info(f"Generating completeness report for {tier}: {start_date.date()} to {end_date.date()}")

        report = CompletenessReport(tier=tier, date_range_start=start_date, date_range_end=end_date)

        if tier == "ALL":
            assets = Asset.objects.filter(category=Asset.Category.CRYPTO, active=True)
        else:
            assets = Asset.objects.filter(category=Asset.Category.CRYPTO, tier=tier, active=True)

        logger.info(f"Analyzing {assets.count()} assets")

        for interval_minutes in intervals:
            interval_completeness = self._analyze_interval(
                assets=list(assets),
                interval_minutes=interval_minutes,
                start_date=start_date,
                end_date=end_date,
            )
            report.intervals[interval_minutes] = interval_completeness

        logger.info(
            f"Report generated: {report.overall_completeness_pct:.1f}% overall completeness, "
            f"{report.total_gaps} total gaps"
        )

        return report

    def _analyze_interval(
        self,
        assets: List[Asset],
        interval_minutes: int,
        start_date: datetime,
        end_date: datetime,
    ) -> IntervalCompleteness:
        logger.debug(f"Analyzing {interval_minutes}min interval")

        asset_completeness_list = []
        total_completeness = 0.0
        complete_count = 0
        total_gaps = 0
        total_fillable = 0
        total_unfillable = 0

        for asset in assets:
            completeness = self._analyze_asset(
                asset=asset,
                interval_minutes=interval_minutes,
                start_date=start_date,
                end_date=end_date,
            )

            asset_completeness_list.append(completeness)
            total_completeness += completeness.completeness_pct

            if completeness.is_complete:
                complete_count += 1

            total_gaps += completeness.gaps_count
            total_fillable += completeness.fillable_gaps
            total_unfillable += completeness.unfillable_gaps

        avg_completeness = total_completeness / len(assets) if assets else 0.0

        return IntervalCompleteness(
            interval_minutes=interval_minutes,
            total_assets=len(assets),
            complete_assets=complete_count,
            partial_assets=len(assets) - complete_count,
            avg_completeness_pct=avg_completeness,
            total_gaps=total_gaps,
            fillable_gaps=total_fillable,
            unfillable_gaps=total_unfillable,
            assets=asset_completeness_list,
        )

    def _analyze_asset(
        self,
        asset: Asset,
        interval_minutes: int,
        start_date: datetime,
        end_date: datetime,
    ) -> AssetCompleteness:
        # Calculate expected candles
        expected_candles = self._calculate_expected_candles(
            start_date=start_date, end_date=end_date, interval_minutes=interval_minutes
        )

        actual_candles = self._count_actual_candles(
            asset=asset, interval_minutes=interval_minutes, start_date=start_date, end_date=end_date
        )

        # Calculate completeness percentage
        completeness_pct = (actual_candles / expected_candles * 100) if expected_candles > 0 else 0.0

        gaps = GapRecord.objects.filter(
            asset=asset,
            interval_minutes=interval_minutes,
            gap_start__gte=start_date,
            gap_end__lte=end_date,
        )

        gaps_count = gaps.count()
        fillable_gaps = gaps.filter(is_api_fillable=True).count()
        unfillable_gaps = gaps.filter(is_api_fillable=False).count()

        return AssetCompleteness(
            asset=asset,
            interval_minutes=interval_minutes,
            expected_candles=expected_candles,
            actual_candles=actual_candles,
            completeness_pct=completeness_pct,
            gaps_count=gaps_count,
            fillable_gaps=fillable_gaps,
            unfillable_gaps=unfillable_gaps,
        )

    def _calculate_expected_candles(self, start_date: datetime, end_date: datetime, interval_minutes: int) -> int:
        total_minutes = (end_date - start_date).total_seconds() / 60
        expected = int(total_minutes / interval_minutes)
        return expected

    def _count_actual_candles(
        self, asset: Asset, interval_minutes: int, start_date: datetime, end_date: datetime
    ) -> int:
        try:
            count = self.questdb_client.count_candles(
                asset_id=asset.id,
                interval_minutes=interval_minutes,
                start_date=start_date,
                end_date=end_date,
            )
            return count

        except Exception as e:
            logger.error(
                f"Error counting candles for {asset.ticker} {interval_minutes}min: {e}",
                exc_info=True,
            )
            return 0

    def display_report(self, report: CompletenessReport):
        print("\n╔══════════════════════════════════════════════════════════╗")
        print(f"║  {report.tier} Data Completeness Report                        ")
        print(f"║  Date Range: {report.date_range_start.date()} to {report.date_range_end.date()}")
        print(f"║  Intervals: {', '.join(f'{i}min' for i in report.intervals.keys())}")
        print("╚══════════════════════════════════════════════════════════╝\n")

        print("Overall Statistics:")
        print(f"• Total Assets: {report.total_assets}")
        print(f"• Overall Completeness: {report.overall_completeness_pct:.1f}%")
        print(f"• Total Gaps: {report.total_gaps}")
        print()

        print("Interval Breakdown:\n")
        for interval_minutes, interval_comp in sorted(report.intervals.items()):
            print(
                f"{interval_minutes}min ({'Hourly' if interval_minutes == 60 else 'Daily' if interval_minutes == 1440 else f'{interval_minutes}min'}):"
            )
            print(f"• Average Completeness: {interval_comp.avg_completeness_pct:.1f}%")
            print(f"• Complete Assets: {interval_comp.complete_assets}/{interval_comp.total_assets}")
            print(f"• Partial Assets: {interval_comp.partial_assets}")
            print(f"• Total Gaps: {interval_comp.total_gaps}")
            print(f"  - API-Fillable: {interval_comp.fillable_gaps}")
            print(f"  - Require CSV: {interval_comp.unfillable_gaps}")
            print()

        print("Assets Requiring Attention:\n")
        attention_count = 0

        for interval_minutes, interval_comp in sorted(report.intervals.items()):
            assets_with_gaps = [a for a in interval_comp.assets if a.has_gaps]

            if assets_with_gaps:
                for asset_comp in sorted(assets_with_gaps, key=lambda x: x.completeness_pct)[:5]:
                    attention_count += 1
                    print(f"{attention_count}. {asset_comp.asset.ticker} ({asset_comp.asset.tier})")
                    print(f"   {interval_minutes}min: {asset_comp.completeness_pct:.1f}% complete")
                    print(f"   Missing: {asset_comp.expected_candles - asset_comp.actual_candles:,} candles")
                    print(f"   Gaps: {asset_comp.gaps_count} total")

                    if asset_comp.fillable_gaps > 0:
                        print(f"   → {asset_comp.fillable_gaps} gaps can be filled via API")

                    if asset_comp.unfillable_gaps > 0:
                        print(f"   → {asset_comp.unfillable_gaps} gaps require CSV download")

                    print()

        if attention_count == 0:
            print("✓ All assets are 100% complete!")
            print()

        total_fillable = sum(i.fillable_gaps for i in report.intervals.values())
        total_unfillable = sum(i.unfillable_gaps for i in report.intervals.values())

        if total_fillable > 0 or total_unfillable > 0:
            print("Recommended Actions:\n")

            if total_fillable > 0:
                print(f"1. Backfill {total_fillable} API-fillable gaps:")
                print(f"   python manage.py backfill_kraken_gaps --tier {report.tier} --only-fillable\n")

            if total_unfillable > 0:
                print(f"2. Download {total_unfillable} CSV files for unfillable gaps:")
                print("   (Run gap detection to generate CSV download list)\n")

                print("3. Re-run ingestion after CSV download:")
                print(f"   python manage.py ingest_kraken_unified --tier {report.tier}\n")

    def export_report_json(self, report: CompletenessReport, output_file: str):
        import json

        data = {
            "tier": report.tier,
            "date_range": {
                "start": report.date_range_start.isoformat(),
                "end": report.date_range_end.isoformat(),
            },
            "generated_at": report.generated_at.isoformat(),
            "overall_completeness_pct": report.overall_completeness_pct,
            "total_assets": report.total_assets,
            "total_gaps": report.total_gaps,
            "intervals": {},
        }

        for interval_minutes, interval_comp in report.intervals.items():
            data["intervals"][interval_minutes] = {
                "avg_completeness_pct": interval_comp.avg_completeness_pct,
                "complete_assets": interval_comp.complete_assets,
                "partial_assets": interval_comp.partial_assets,
                "total_gaps": interval_comp.total_gaps,
                "fillable_gaps": interval_comp.fillable_gaps,
                "unfillable_gaps": interval_comp.unfillable_gaps,
                "assets": [
                    {
                        "ticker": a.asset.ticker,
                        "tier": a.asset.tier,
                        "completeness_pct": a.completeness_pct,
                        "expected_candles": a.expected_candles,
                        "actual_candles": a.actual_candles,
                        "gaps_count": a.gaps_count,
                    }
                    for a in interval_comp.assets
                ],
            }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported completeness report to {output_file}")

    def compare_reports(self, report1: CompletenessReport, report2: CompletenessReport) -> dict:
        comparison = {
            "completeness_change": report2.overall_completeness_pct - report1.overall_completeness_pct,
            "gaps_change": report2.total_gaps - report1.total_gaps,
            "intervals": {},
        }

        for interval in set(report1.intervals.keys()) | set(report2.intervals.keys()):
            if interval in report1.intervals and interval in report2.intervals:
                int1 = report1.intervals[interval]
                int2 = report2.intervals[interval]

                comparison["intervals"][interval] = {
                    "completeness_change": int2.avg_completeness_pct - int1.avg_completeness_pct,
                    "complete_assets_change": int2.complete_assets - int1.complete_assets,
                    "gaps_change": int2.total_gaps - int1.total_gaps,
                }

        return comparison
