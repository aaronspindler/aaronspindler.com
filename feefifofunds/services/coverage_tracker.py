"""
Coverage Tracker for maintaining DataCoverageRange records.

This service updates DataCoverageRange entries after data ingestion to track
what data exists for each asset/interval, enabling efficient gap detection.
"""

import logging
from datetime import datetime

from django.db import transaction

from feefifofunds.models import Asset, DataCoverageRange, FileIngestionRecord, IngestionJob
from feefifofunds.services.questdb_client import QuestDBClient

logger = logging.getLogger(__name__)


class CoverageTracker:
    """
    Tracks data coverage ranges for assets/intervals.

    After data ingestion, this service queries QuestDB to find the actual
    date ranges present and updates DataCoverageRange accordingly.
    Overlapping ranges are automatically merged.
    """

    def __init__(self, database: str = "questdb"):
        """
        Initialize coverage tracker.

        Args:
            database: Database alias to query (default: questdb)
        """
        self.database = database
        self.questdb_client = QuestDBClient(database=database)

    def update_coverage_after_ingestion(self, job: IngestionJob) -> dict:
        """
        Update coverage ranges for all assets/intervals in an ingestion job.

        This should be called after CSV files are ingested to update the
        DataCoverageRange table with actual data present in QuestDB.

        Args:
            job: IngestionJob that was completed

        Returns:
            Dictionary with update statistics
        """
        logger.info(f"Updating coverage ranges for job {job.job_id}")

        stats = {
            "ranges_created": 0,
            "ranges_updated": 0,
            "ranges_merged": 0,
            "assets_processed": 0,
        }

        # Get all successfully ingested files
        ingested_files = FileIngestionRecord.objects.filter(job=job, status=FileIngestionRecord.Status.COMPLETED)

        # Group by asset/interval
        asset_intervals = {}
        for file_record in ingested_files:
            key = (file_record.asset.id, file_record.interval_minutes)
            if key not in asset_intervals:
                asset_intervals[key] = []
            asset_intervals[key].append(file_record)

        logger.info(f"Processing {len(asset_intervals)} asset/interval combinations")

        # Update coverage for each asset/interval
        for (asset_id, interval_minutes), _file_records in asset_intervals.items():
            try:
                asset = Asset.objects.get(id=asset_id)

                # Query QuestDB for actual date range
                date_range = self._query_date_range_from_questdb(asset, interval_minutes)

                if not date_range:
                    logger.warning(
                        f"No data found in QuestDB for {asset.ticker} {interval_minutes}min "
                        f"despite successful ingestion"
                    )
                    continue

                start_date, end_date, record_count = date_range

                # Create or update coverage range
                self._create_or_update_coverage_range(
                    asset=asset,
                    interval_minutes=interval_minutes,
                    start_date=start_date,
                    end_date=end_date,
                    record_count=record_count,
                    source=DataCoverageRange.Source.CSV,  # Assuming CSV ingestion
                )

                # Merge overlapping ranges
                merged = DataCoverageRange.merge_overlapping_ranges(asset, interval_minutes)
                if merged:
                    stats["ranges_merged"] += len(merged) - 1  # Number of merges performed

                stats["assets_processed"] += 1

            except Exception as e:
                logger.error(
                    f"Error updating coverage for asset {asset_id}, interval {interval_minutes}min: {e}",
                    exc_info=True,
                )

        logger.info(
            f"Coverage update complete: {stats['ranges_created']} created, "
            f"{stats['ranges_updated']} updated, {stats['ranges_merged']} merged"
        )

        return stats

    def update_coverage_for_asset(
        self,
        asset: Asset,
        interval_minutes: int,
        source: str = "CSV",
    ) -> DataCoverageRange | None:
        """
        Update coverage range for a single asset/interval.

        Queries QuestDB for the actual date range and creates/updates
        the DataCoverageRange entry.

        Args:
            asset: Asset to update
            interval_minutes: Interval in minutes
            source: Data source type (CSV, API, or MIXED)

        Returns:
            Updated DataCoverageRange or None if no data found
        """
        logger.debug(f"Updating coverage for {asset.ticker} {interval_minutes}min")

        # Query QuestDB for date range
        date_range = self._query_date_range_from_questdb(asset, interval_minutes)

        if not date_range:
            logger.warning(f"No data found in QuestDB for {asset.ticker} {interval_minutes}min")
            return None

        start_date, end_date, record_count = date_range

        # Create or update coverage range
        coverage = self._create_or_update_coverage_range(
            asset=asset,
            interval_minutes=interval_minutes,
            start_date=start_date,
            end_date=end_date,
            record_count=record_count,
            source=source,
        )

        # Merge overlapping ranges
        DataCoverageRange.merge_overlapping_ranges(asset, interval_minutes)

        return coverage

    def _query_date_range_from_questdb(
        self, asset: Asset, interval_minutes: int
    ) -> tuple[datetime, datetime, int] | None:
        """
        Query QuestDB to find the actual date range for an asset/interval.

        Args:
            asset: Asset to query
            interval_minutes: Interval in minutes

        Returns:
            Tuple of (start_date, end_date, record_count) or None if no data
        """
        try:
            # Use safe parameterized query
            result = self.questdb_client.get_date_range_for_asset(asset_id=asset.id, interval_minutes=interval_minutes)

            if not result:
                return None

            start_date, end_date, record_count = result

            logger.debug(
                f"Found data for {asset.ticker} {interval_minutes}min: "
                f"{start_date.date()} to {end_date.date()} ({record_count:,} records)"
            )

            return start_date, end_date, record_count

        except Exception as e:
            logger.error(f"Error querying QuestDB for {asset.ticker} {interval_minutes}min: {e}", exc_info=True)
            return None

    def _create_or_update_coverage_range(
        self,
        asset: Asset,
        interval_minutes: int,
        start_date: datetime,
        end_date: datetime,
        record_count: int,
        source: str,
    ) -> DataCoverageRange:
        """
        Create or update a DataCoverageRange entry.

        If an overlapping range exists, it will be updated. Otherwise,
        a new range is created.

        Args:
            asset: Asset
            interval_minutes: Interval in minutes
            start_date: Range start
            end_date: Range end
            record_count: Number of records in range
            source: Data source type

        Returns:
            DataCoverageRange instance
        """
        with transaction.atomic():
            # Check for existing overlapping ranges
            existing = DataCoverageRange.objects.filter(
                asset=asset,
                interval_minutes=interval_minutes,
                start_date__lte=end_date,
                end_date__gte=start_date,
            ).first()

            if existing:
                # Update existing range
                existing.start_date = min(existing.start_date, start_date)
                existing.end_date = max(existing.end_date, end_date)
                existing.record_count = record_count
                existing.source = source
                existing.save()

                logger.debug(
                    f"Updated coverage range for {asset.ticker} {interval_minutes}min: "
                    f"{existing.start_date.date()} to {existing.end_date.date()}"
                )

                return existing
            else:
                # Create new range
                coverage = DataCoverageRange.objects.create(
                    asset=asset,
                    interval_minutes=interval_minutes,
                    start_date=start_date,
                    end_date=end_date,
                    record_count=record_count,
                    source=source,
                )

                logger.debug(
                    f"Created coverage range for {asset.ticker} {interval_minutes}min: "
                    f"{start_date.date()} to {end_date.date()} ({record_count:,} records)"
                )

                return coverage

    def get_coverage_summary(self, tier: str | None = None, interval_minutes: int | None = None) -> dict:
        """
        Get a summary of data coverage.

        Args:
            tier: Filter by asset tier (optional)
            interval_minutes: Filter by interval (optional)

        Returns:
            Dictionary with coverage statistics
        """
        query = DataCoverageRange.objects.all()

        if tier:
            query = query.filter(asset__tier=tier)

        if interval_minutes:
            query = query.filter(interval_minutes=interval_minutes)

        total_ranges = query.count()
        total_records = sum(r.record_count for r in query)

        # Get date range
        if total_ranges > 0:
            earliest = min(r.start_date for r in query)
            latest = max(r.end_date for r in query)
        else:
            earliest = None
            latest = None

        # Count by source
        source_counts = {}
        for source_choice in DataCoverageRange.Source.choices:
            source_value = source_choice[0]
            count = query.filter(source=source_value).count()
            if count > 0:
                source_counts[source_value] = count

        return {
            "total_ranges": total_ranges,
            "total_records": total_records,
            "earliest_date": earliest,
            "latest_date": latest,
            "by_source": source_counts,
        }

    def verify_coverage_integrity(self, asset: Asset, interval_minutes: int) -> dict:
        """
        Verify that coverage ranges match actual data in QuestDB.

        This is useful for debugging and validation.

        Args:
            asset: Asset to verify
            interval_minutes: Interval to verify

        Returns:
            Dictionary with verification results
        """
        # Get coverage ranges from database
        db_ranges = list(
            DataCoverageRange.objects.filter(asset=asset, interval_minutes=interval_minutes).order_by("start_date")
        )

        # Get actual data from QuestDB
        actual_range = self._query_date_range_from_questdb(asset, interval_minutes)

        results = {
            "asset": asset.ticker,
            "interval_minutes": interval_minutes,
            "db_ranges_count": len(db_ranges),
            "matches_questdb": False,
            "issues": [],
        }

        if not actual_range:
            if db_ranges:
                results["issues"].append("Coverage ranges exist but no data in QuestDB")
            else:
                results["matches_questdb"] = True  # Both empty
            return results

        actual_start, actual_end, actual_count = actual_range

        if not db_ranges:
            results["issues"].append("Data exists in QuestDB but no coverage ranges in database")
            return results

        # Check if ranges cover the actual data
        db_start = min(r.start_date for r in db_ranges)
        db_end = max(r.end_date for r in db_ranges)

        if db_start > actual_start:
            results["issues"].append(
                f"Coverage starts later than actual data: DB={db_start.date()}, QuestDB={actual_start.date()}"
            )

        if db_end < actual_end:
            results["issues"].append(
                f"Coverage ends earlier than actual data: DB={db_end.date()}, QuestDB={actual_end.date()}"
            )

        # Check record counts
        db_total_records = sum(r.record_count for r in db_ranges)
        if db_total_records != actual_count:
            results["issues"].append(f"Record count mismatch: DB={db_total_records:,}, QuestDB={actual_count:,}")

        results["matches_questdb"] = len(results["issues"]) == 0

        return results
