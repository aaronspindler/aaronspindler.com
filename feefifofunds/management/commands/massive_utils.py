from datetime import date, timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from feefifofunds.models import DataSync, Fund
from feefifofunds.models.performance import FundPerformance
from feefifofunds.services.data_sources.massive import MAX_FREE_TIER_DAYS, MassiveDataSource


def initialize_data_source(stdout, style):
    try:
        return MassiveDataSource()
    except Exception as e:
        stdout.write(style.ERROR(f"❌ Failed to initialize Massive.com: {e}"))
        stdout.write("\n💡 Make sure MASSIVE_API_KEY is set in environment variables or settings")
        return None


def get_date_range(days: int):
    days = min(days, MAX_FREE_TIER_DAYS)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


@transaction.atomic
def process_fund_creation(data_source: MassiveDataSource, ticker: str, stdout, style) -> Optional[Fund]:
    stdout.write(f"🔍 Fetching fund info for {ticker}...")
    fund_info = data_source.fetch_fund_info(ticker)
    fund = Fund.objects.create(
        ticker=fund_info.ticker,
        name=fund_info.name,
        description=fund_info.description or "",
        exchange=fund_info.exchange or "",
        current_value=fund_info.current_price,
        previous_value=fund_info.previous_close,
        quote_currency=fund_info.currency,
        website=fund_info.website or "",
        aum=fund_info.aum,
    )
    stdout.write(style.SUCCESS(f"✅ Created fund: {fund}"))
    return fund


@transaction.atomic
def save_performance_data(
    fund: Fund,
    performance_data: list,
    data_source: MassiveDataSource,
    start_date: date,
    end_date: date,
    skip_existing: bool = False,
    stdout=None,
):
    sync_record = data_source.create_sync_record(
        sync_type=DataSync.SyncType.PRICES,
        fund=fund,
        request_params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
    )

    created_count = 0
    updated_count = 0
    skipped_count = 0

    # Build list of performance records to insert/update
    performance_records = []
    for perf_dto in performance_data:
        if skip_existing:
            existing = FundPerformance.objects.filter(
                asset=fund, date=perf_dto.date, interval=perf_dto.interval
            ).exists()
            if existing:
                skipped_count += 1
                continue

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

    # Use bulk_create with update_conflicts for efficient upsert
    if performance_records:
        FundPerformance.objects.bulk_create(
            performance_records,
            update_conflicts=True,
            update_fields=[
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "adjusted_close",
                "volume",
                "dividend",
                "split_ratio",
                "data_source",
                "updated_at",
            ],
            unique_fields=["asset", "date", "interval"],
        )
        created_count = len(performance_records)

    if performance_data:
        fund.current_value = performance_data[-1].close_price
        fund.last_price_update = timezone.now()
        fund.save(update_fields=["current_value", "last_price_update"])

    sync_record.records_fetched = len(performance_data)
    sync_record.records_created = created_count
    sync_record.records_updated = updated_count
    sync_record.mark_complete(success=True)

    return created_count, updated_count, skipped_count, sync_record


def handle_sync_error(sync_record: Optional[DataSync], error_message: str):
    if sync_record is not None:
        sync_record.mark_complete(success=False, error_message=error_message)
