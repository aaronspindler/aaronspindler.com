import logging
from datetime import datetime

from django.db import transaction

from feefifofunds.models import Asset, DataCoverageRange, FileIngestionRecord, IngestionJob
from feefifofunds.services.questdb_client import QuestDBClient

logger = logging.getLogger(__name__)


class CoverageTracker:
    def __init__(self, database: str = "questdb"):
        self.database = database
        self.questdb_client = QuestDBClient(database=database)

    def update_coverage_after_ingestion(self, job: IngestionJob) -> dict:
        logger.info(f"Updating coverage ranges for job {job.job_id}")

        stats = {
            "ranges_created": 0,
            "ranges_updated": 0,
            "ranges_merged": 0,
            "assets_processed": 0,
        }

        ingested_files = FileIngestionRecord.objects.filter(job=job, status=FileIngestionRecord.Status.COMPLETED)

        asset_intervals = {}
        for file_record in ingested_files:
            key = (file_record.asset.id, file_record.interval_minutes)
            if key not in asset_intervals:
                asset_intervals[key] = []
            asset_intervals[key].append(file_record)

        logger.info(f"Processing {len(asset_intervals)} asset/interval combinations")

        for (asset_id, interval_minutes), _file_records in asset_intervals.items():
            try:
                asset = Asset.objects.get(id=asset_id)

                date_range = self._query_date_range_from_questdb(asset, interval_minutes)

                if not date_range:
                    logger.warning(
                        f"No data found in QuestDB for {asset.ticker} {interval_minutes}min "
                        f"despite successful ingestion"
                    )
                    continue

                start_date, end_date, record_count = date_range

                self._create_or_update_coverage_range(
                    asset=asset,
                    interval_minutes=interval_minutes,
                    start_date=start_date,
                    end_date=end_date,
                    record_count=record_count,
                    source=DataCoverageRange.Source.CSV,  # Assuming CSV ingestion
                )

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
        logger.debug(f"Updating coverage for {asset.ticker} {interval_minutes}min")

        date_range = self._query_date_range_from_questdb(asset, interval_minutes)

        if not date_range:
            logger.warning(f"No data found in QuestDB for {asset.ticker} {interval_minutes}min")
            return None

        start_date, end_date, record_count = date_range

        coverage = self._create_or_update_coverage_range(
            asset=asset,
            interval_minutes=interval_minutes,
            start_date=start_date,
            end_date=end_date,
            record_count=record_count,
            source=source,
        )

        DataCoverageRange.merge_overlapping_ranges(asset, interval_minutes)

        return coverage

    def _query_date_range_from_questdb(
        self, asset: Asset, interval_minutes: int
    ) -> tuple[datetime, datetime, int] | None:
        try:
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
        with transaction.atomic():
            existing = DataCoverageRange.objects.filter(
                asset=asset,
                interval_minutes=interval_minutes,
                start_date__lte=end_date,
                end_date__gte=start_date,
            ).first()

            if existing:
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
        query = DataCoverageRange.objects.all()

        if tier:
            query = query.filter(asset__tier=tier)

        if interval_minutes:
            query = query.filter(interval_minutes=interval_minutes)

        total_ranges = query.count()
        total_records = sum(r.record_count for r in query)

        if total_ranges > 0:
            earliest = min(r.start_date for r in query)
            latest = max(r.end_date for r in query)
        else:
            earliest = None
            latest = None

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
        db_ranges = list(
            DataCoverageRange.objects.filter(asset=asset, interval_minutes=interval_minutes).order_by("start_date")
        )

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

        db_total_records = sum(r.record_count for r in db_ranges)
        if db_total_records != actual_count:
            results["issues"].append(f"Record count mismatch: DB={db_total_records:,}, QuestDB={actual_count:,}")

        results["matches_questdb"] = len(results["issues"]) == 0

        return results
