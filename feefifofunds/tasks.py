"""
Celery tasks for FeeFiFoFunds data ingestion and maintenance.

These tasks are designed to run on a schedule via Celery Beat to keep
Kraken OHLCV data up-to-date automatically.
"""

import logging
from datetime import datetime, timedelta
from typing import List

from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="feefifofunds.backfill_gaps_incremental")
def backfill_gaps_incremental(
    self,
    tier: str = "TIER1",
    intervals: List[int] | None = None,
    lookback_days: int = 7,
    max_gaps_per_asset: int = 10,
):
    """
    Incrementally backfill gaps from the last saved data point to now.

    This task is designed to run on a schedule (e.g., daily) to keep data current.
    It finds the last data point for each asset/interval, checks if there's a gap
    to today, and backfills via Kraken API if within the 720-candle limit.

    Args:
        tier: Asset tier to process (TIER1, TIER2, TIER3, TIER4, or ALL)
        intervals: List of interval minutes to process (default: [60, 1440])
        lookback_days: How many days back to check for gaps (default: 7)
        max_gaps_per_asset: Maximum gaps to fill per asset (default: 10)

    Returns:
        dict: Summary of backfill operation

    Example:
        # Run via Celery Beat (scheduled)
        CELERY_BEAT_SCHEDULE = {
            'backfill-kraken-gaps-daily': {
                'task': 'feefifofunds.backfill_gaps_incremental',
                'schedule': crontab(hour=2, minute=0),  # 2 AM daily
                'kwargs': {'tier': 'TIER1', 'intervals': [60, 1440]}
            }
        }

        # Or trigger manually
        from feefifofunds.tasks import backfill_gaps_incremental
        result = backfill_gaps_incremental.delay(tier='TIER1')
    """
    from feefifofunds.models import Asset, GapRecord
    from feefifofunds.services.data_sources.kraken import KrakenDataSource
    from feefifofunds.services.questdb_client import QuestDBClient

    logger.info(f"Starting incremental gap backfill: tier={tier}, intervals={intervals}, lookback_days={lookback_days}")

    if intervals is None:
        intervals = [60, 1440]  # Default: hourly and daily

    # Get assets for tier
    if tier == "ALL":
        assets = Asset.objects.filter(category=Asset.Category.CRYPTO, active=True)
    else:
        assets = Asset.objects.filter(category=Asset.Category.CRYPTO, tier=tier, active=True)

    logger.info(f"Processing {assets.count()} assets for tier {tier}")

    # Initialize Kraken data source and QuestDB client
    kraken = KrakenDataSource(database="questdb")
    questdb = QuestDBClient(database="questdb")

    # Summary statistics
    summary = {
        "task_id": self.request.id,
        "tier": tier,
        "intervals": intervals,
        "assets_processed": 0,
        "gaps_detected": 0,
        "gaps_filled": 0,
        "gaps_unfillable": 0,
        "gaps_failed": 0,
        "total_candles_filled": 0,
        "errors": [],
    }

    cutoff_date = datetime.now() - timedelta(days=lookback_days)

    for asset in assets:
        asset_summary = {
            "ticker": asset.ticker,
            "intervals_processed": 0,
            "gaps_found": 0,
            "gaps_filled": 0,
        }

        for interval_minutes in intervals:
            try:
                # Find last data point for this asset/interval
                last_timestamp = questdb.get_last_timestamp(asset.id, interval_minutes)

                if not last_timestamp:
                    logger.warning(
                        f"No existing data for {asset.ticker} {interval_minutes}min - skipping incremental backfill"
                    )
                    continue

                # Only process if last data point is recent (within lookback window)
                if last_timestamp < cutoff_date:
                    logger.debug(
                        f"Last data point for {asset.ticker} {interval_minutes}min "
                        f"is too old ({last_timestamp}) - skipping"
                    )
                    continue

                # Calculate gap from last data point to now
                now = datetime.now()
                gap_start = last_timestamp + timedelta(minutes=interval_minutes)  # Next expected candle
                gap_end = now

                # Check if there's actually a gap (at least 1 candle missing)
                gap_minutes = (gap_end - gap_start).total_seconds() / 60
                if gap_minutes < interval_minutes:
                    logger.debug(f"No gap for {asset.ticker} {interval_minutes}min - data is current")
                    continue

                missing_candles = int(gap_minutes / interval_minutes)

                # Check API fillability (720-candle limit)
                is_api_fillable, overflow_candles, candles_from_today = GapRecord.calculate_api_fillability(
                    interval_minutes=interval_minutes, gap_start=gap_start, now=now
                )

                if not is_api_fillable:
                    logger.warning(
                        f"Gap for {asset.ticker} {interval_minutes}min is unfillable "
                        f"(beyond 720-candle limit by {overflow_candles} candles)"
                    )

                    # Create GapRecord for tracking
                    with transaction.atomic():
                        gap_record = GapRecord.objects.create(
                            asset=asset,
                            interval_minutes=interval_minutes,
                            gap_start=gap_start,
                            gap_end=gap_end,
                            missing_candles=missing_candles,
                            is_api_fillable=False,
                            overflow_candles=overflow_candles,
                            candles_from_today=candles_from_today,
                            status=GapRecord.Status.UNFILLABLE,
                            required_csv_file=f"{asset.ticker}USD_{interval_minutes}.csv",
                        )

                    summary["gaps_unfillable"] += 1
                    asset_summary["gaps_found"] += 1
                    continue

                # Gap is fillable - backfill via API
                logger.info(
                    f"Backfilling gap for {asset.ticker} {interval_minutes}min: "
                    f"{gap_start} to {gap_end} ({missing_candles} candles)"
                )

                # Create GapRecord before backfilling
                with transaction.atomic():
                    gap_record = GapRecord.objects.create(
                        asset=asset,
                        interval_minutes=interval_minutes,
                        gap_start=gap_start,
                        gap_end=gap_end,
                        missing_candles=missing_candles,
                        is_api_fillable=True,
                        overflow_candles=0,
                        candles_from_today=candles_from_today,
                        status=GapRecord.Status.DETECTED,
                    )

                try:
                    # Mark as backfilling
                    gap_record.mark_backfilling()

                    # Fetch and save data via Kraken API
                    candles_filled = kraken.fetch_and_save_historical_prices(
                        asset=asset,
                        interval_minutes=interval_minutes,
                        start_date=gap_start,
                        end_date=gap_end,
                    )

                    # Mark as filled
                    gap_record.mark_filled()

                    logger.info(f"✓ Filled gap for {asset.ticker} {interval_minutes}min: {candles_filled} candles")

                    summary["gaps_filled"] += 1
                    summary["total_candles_filled"] += candles_filled
                    asset_summary["gaps_filled"] += 1

                except Exception as e:
                    error_msg = f"Failed to backfill {asset.ticker} {interval_minutes}min: {str(e)}"
                    logger.error(error_msg, exc_info=True)

                    # Mark gap as failed
                    gap_record.mark_failed(str(e))

                    summary["gaps_failed"] += 1
                    summary["errors"].append(error_msg)

                summary["gaps_detected"] += 1
                asset_summary["gaps_found"] += 1
                asset_summary["intervals_processed"] += 1

                # Respect rate limits
                import time

                time.sleep(1)  # 1 second between API calls

                # Check if we've hit the max gaps per asset
                if asset_summary["gaps_filled"] >= max_gaps_per_asset:
                    logger.info(
                        f"Reached max gaps per asset ({max_gaps_per_asset}) "
                        f"for {asset.ticker} - skipping remaining intervals"
                    )
                    break

            except Exception as e:
                error_msg = f"Error processing {asset.ticker} {interval_minutes}min: {str(e)}"
                logger.error(error_msg, exc_info=True)
                summary["errors"].append(error_msg)

        summary["assets_processed"] += 1

        logger.info(
            f"Completed {asset.ticker}: "
            f"{asset_summary['gaps_filled']}/{asset_summary['gaps_found']} gaps filled "
            f"across {asset_summary['intervals_processed']} intervals"
        )

    logger.info(
        f"Incremental backfill completed: "
        f"{summary['gaps_filled']}/{summary['gaps_detected']} gaps filled, "
        f"{summary['total_candles_filled']} total candles, "
        f"{summary['gaps_unfillable']} unfillable, "
        f"{summary['gaps_failed']} failed"
    )

    return summary


@shared_task(name="feefifofunds.cleanup_old_gap_records")
def cleanup_old_gap_records(days: int = 90):
    """
    Clean up old GapRecord entries that have been resolved.

    Keeps unfillable gaps indefinitely as they serve as documentation
    of what CSV files are needed.

    Args:
        days: Delete filled/failed gaps older than this many days (default: 90)

    Returns:
        dict: Count of deleted records by status
    """
    from feefifofunds.models import GapRecord

    cutoff_date = datetime.now() - timedelta(days=days)

    # Delete old filled gaps
    filled_deleted = GapRecord.objects.filter(status=GapRecord.Status.FILLED, filled_at__lt=cutoff_date).delete()[0]

    # Delete old failed gaps (give them a chance to be retried)
    failed_deleted = GapRecord.objects.filter(status=GapRecord.Status.FAILED, detected_at__lt=cutoff_date).delete()[0]

    logger.info(f"Cleaned up {filled_deleted} filled and {failed_deleted} failed gap records older than {days} days")

    return {"filled_deleted": filled_deleted, "failed_deleted": failed_deleted}


@shared_task(name="feefifofunds.report_data_completeness")
def report_data_completeness(tier: str = "TIER1", intervals: List[int] | None = None):
    """
    Generate and log data completeness report for a tier.

    This task can be run on a schedule to monitor data quality and
    identify assets that need attention.

    Args:
        tier: Asset tier to report on (TIER1, TIER2, TIER3, TIER4)
        intervals: List of interval minutes to report on (default: [60, 1440])

    Returns:
        dict: Completeness metrics
    """
    from feefifofunds.models import Asset, GapRecord

    if intervals is None:
        intervals = [60, 1440]

    assets = Asset.objects.filter(category=Asset.Category.CRYPTO, tier=tier, active=True)

    report = {"tier": tier, "intervals": {}, "total_assets": assets.count(), "assets_with_gaps": 0}

    for interval_minutes in intervals:
        # Count gaps per status
        gaps = GapRecord.objects.filter(
            asset__tier=tier, asset__category=Asset.Category.CRYPTO, interval_minutes=interval_minutes
        )

        fillable_gaps = gaps.filter(
            is_api_fillable=True, status__in=[GapRecord.Status.DETECTED, GapRecord.Status.FAILED]
        ).count()

        unfillable_gaps = gaps.filter(status=GapRecord.Status.UNFILLABLE).count()

        report["intervals"][interval_minutes] = {
            "fillable_gaps": fillable_gaps,
            "unfillable_gaps": unfillable_gaps,
            "total_gaps": fillable_gaps + unfillable_gaps,
        }

    # Count assets with any gaps
    assets_with_gaps = (
        GapRecord.objects.filter(asset__tier=tier, asset__category=Asset.Category.CRYPTO)
        .values("asset")
        .distinct()
        .count()
    )

    report["assets_with_gaps"] = assets_with_gaps
    report["completeness_pct"] = (
        (report["total_assets"] - assets_with_gaps) / report["total_assets"] * 100 if report["total_assets"] > 0 else 0
    )

    logger.info(
        f"Data completeness for {tier}: {report['completeness_pct']:.1f}% "
        f"({report['assets_with_gaps']}/{report['total_assets']} assets have gaps)"
    )

    for interval, stats in report["intervals"].items():
        logger.info(
            f"  {interval}min: {stats['fillable_gaps']} fillable gaps, {stats['unfillable_gaps']} unfillable gaps"
        )

    return report


@shared_task(name="feefifofunds.validate_recent_data")
def validate_recent_data(hours: int = 24):
    """
    Validate that recent data exists for all active TIER1/TIER2 assets.

    This task can be used as a monitoring/alerting mechanism to detect
    data ingestion issues early.

    Args:
        hours: Check if data exists within last N hours (default: 24)

    Returns:
        dict: Validation results with list of assets missing recent data
    """
    from feefifofunds.models import Asset
    from feefifofunds.services.questdb_client import QuestDBClient

    questdb = QuestDBClient(database="questdb")
    cutoff_time = datetime.now() - timedelta(hours=hours)

    # Check TIER1 and TIER2 assets (most critical)
    assets = Asset.objects.filter(category=Asset.Category.CRYPTO, tier__in=["TIER1", "TIER2"], active=True)

    results = {"assets_checked": assets.count(), "assets_missing_data": [], "interval_minutes": 1440}

    for asset in assets:
        last_timestamp = questdb.get_last_timestamp(asset.id, interval_minutes=1440)  # Check daily data

        if not last_timestamp or last_timestamp < cutoff_time:
            results["assets_missing_data"].append(
                {
                    "ticker": asset.ticker,
                    "tier": asset.tier,
                    "last_timestamp": last_timestamp.isoformat() if last_timestamp else None,
                    "hours_behind": int((datetime.now() - last_timestamp).total_seconds() / 3600)
                    if last_timestamp
                    else None,
                }
            )

    if results["assets_missing_data"]:
        logger.warning(
            f"Data validation failed: {len(results['assets_missing_data'])} assets missing data from last {hours} hours"
        )
        for asset_info in results["assets_missing_data"]:
            logger.warning(
                f"  {asset_info['ticker']} ({asset_info['tier']}): {asset_info['hours_behind']}h behind"
                if asset_info["hours_behind"]
                else f"  {asset_info['ticker']} ({asset_info['tier']}): no data found"
            )
    else:
        logger.info(f"Data validation passed: All {results['assets_checked']} assets have recent data")

    return results
