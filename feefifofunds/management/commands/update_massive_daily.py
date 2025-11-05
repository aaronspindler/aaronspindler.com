from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from feefifofunds.models import DataSync, Fund
from feefifofunds.models.performance import FundPerformance

from .massive_utils import get_date_range, handle_sync_error, initialize_data_source


class Command(BaseCommand):
    help = "Fetch daily price updates from Massive.com for all active funds"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "tickers",
            nargs="*",
            type=str,
            help="Optional: Specific ticker symbols to update (default: all active funds)",
        )

        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help="Number of days to fetch (default: 1, useful for catching up after weekends)",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Force update even if data already exists for today",
        )

    def handle(self, *args, **options) -> None:
        tickers = options["tickers"]
        days = options["days"]
        force = options["force"]

        data_source = initialize_data_source(self.stdout, self.style)
        if data_source is None:
            return

        if tickers:
            funds = Fund.objects.filter(ticker__in=tickers, is_active=True)
        else:
            funds = Fund.objects.filter(is_active=True)

        if not funds.exists():
            self.stdout.write(self.style.WARNING("⚠️  No active funds found to update"))
            return

        self.stdout.write(f"📊 Updating {funds.count()} funds with last {days} day(s) of data\n")

        start_date, end_date = get_date_range(days)

        success_count = 0
        error_count = 0
        skipped_count = 0

        for fund in funds:
            sync_record = None

            try:
                if not force:
                    latest_perf = FundPerformance.objects.filter(asset=fund, is_active=True).order_by("-date").first()
                    if latest_perf and latest_perf.date >= date.today():
                        self.stdout.write(f"⏭️  {fund.ticker}: Already up-to-date")
                        skipped_count += 1
                        continue

                self.stdout.write(f"📥 {fund.ticker}: Fetching data...")

                sync_record = data_source.create_sync_record(
                    sync_type=DataSync.SyncType.PRICES,
                    fund=fund,
                    request_params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                )

                performance_data = data_source.fetch_historical_prices(fund.ticker, start_date, end_date)

                if not performance_data:
                    self.stdout.write(self.style.WARNING(f"⚠️  {fund.ticker}: No new data available"))
                    sync_record.mark_complete(success=True)
                    skipped_count += 1
                    continue

                created_count, updated_count = self._save_performance_data(
                    fund=fund,
                    performance_data=performance_data,
                    sync_record=sync_record,
                )

                self.stdout.write(self.style.SUCCESS(f"✅ {fund.ticker}: {created_count} new, {updated_count} updated"))
                success_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ {fund.ticker}: {e}"))
                error_count += 1
                handle_sync_error(sync_record, str(e))

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"✅ Successfully updated: {success_count}")
        if skipped_count > 0:
            self.stdout.write(f"⏭️  Skipped (up-to-date): {skipped_count}")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"❌ Failed: {error_count}"))
        self.stdout.write(f"{'='*60}\n")

    @transaction.atomic
    def _save_performance_data(self, fund: Fund, performance_data: list, sync_record: DataSync) -> tuple[int, int]:
        created_count = 0
        updated_count = 0

        # Build list of performance records to insert/update
        performance_records = []
        for perf_dto in performance_data:
            performance_records.append(
                FundPerformance(
                    asset=fund,
                    date=perf_dto.date,
                    interval=perf_dto.interval,
                    open_price=perf_dto.open_price,
                    high_price=perf_dto.high_price,
                    low_price=perf_dto.low_price,
                    close_price=perf_dto.close_price,
                    adjusted_close=perf_dto.adjusted_close,
                    volume=perf_dto.volume,
                    dividend=perf_dto.dividend,
                    split_ratio=perf_dto.split_ratio,
                    data_source=perf_dto.source,
                )
            )

        # Use raw SQL for TimescaleDB hypertable compatibility
        # bulk_create tries to RETURNING id which fails on tables without id column
        if performance_records:
            from django.db import connection

            with connection.cursor() as cursor:
                for record in performance_records:
                    cursor.execute(
                        """
                        INSERT INTO feefifofunds_performance (
                            created_at, updated_at, is_active, deleted_at,
                            date, interval, value, data_source, data_quality_score,
                            open_price, high_price, low_price, close_price, adjusted_close,
                            volume, dollar_volume, dividend, split_ratio,
                            daily_return, log_return, asset_id
                        ) VALUES (
                            NOW(), NOW(), TRUE, NULL,
                            %s, %s, NULL, %s, NULL,
                            %s, %s, %s, %s, %s,
                            %s, NULL, %s, %s,
                            NULL, NULL, %s
                        )
                        ON CONFLICT (asset_id, date, interval) DO UPDATE SET
                            updated_at = NOW(),
                            open_price = EXCLUDED.open_price,
                            high_price = EXCLUDED.high_price,
                            low_price = EXCLUDED.low_price,
                            close_price = EXCLUDED.close_price,
                            adjusted_close = EXCLUDED.adjusted_close,
                            volume = EXCLUDED.volume,
                            dividend = EXCLUDED.dividend,
                            split_ratio = EXCLUDED.split_ratio,
                            data_source = EXCLUDED.data_source
                        """,
                        [
                            record.date,
                            record.interval,
                            record.data_source,
                            record.open_price,
                            record.high_price,
                            record.low_price,
                            record.close_price,
                            record.adjusted_close,
                            record.volume,
                            record.dividend,
                            record.split_ratio,
                            record.asset.id,
                        ],
                    )
            created_count = len(performance_records)

        latest_price = performance_data[-1].close_price
        fund.previous_value = fund.current_value
        fund.current_value = latest_price
        fund.last_price_update = timezone.now()
        fund.save(update_fields=["previous_value", "current_value", "last_price_update"])

        sync_record.records_fetched = len(performance_data)
        sync_record.records_created = created_count
        sync_record.records_updated = updated_count
        sync_record.mark_complete(success=True)

        return created_count, updated_count
