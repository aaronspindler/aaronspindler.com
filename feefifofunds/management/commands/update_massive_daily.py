"""
Management command to fetch daily price updates from Massive.com.

This command should be run daily (via cron or Celery Beat) to keep fund data up-to-date.

Usage:
    python manage.py update_massive_daily
    python manage.py update_massive_daily SPY QQQ VOO
    python manage.py update_massive_daily --days 5  # Fetch last 5 days
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from feefifofunds.models import DataSync, Fund
from feefifofunds.models.performance import FundPerformance
from feefifofunds.services.data_sources.massive import MassiveDataSource


class Command(BaseCommand):
    help = "Fetch daily price updates from Massive.com for all active funds"

    def add_arguments(self, parser):
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

    def handle(self, *args, **options):
        tickers = options["tickers"]
        days = options["days"]
        force = options["force"]

        try:
            data_source = MassiveDataSource()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to initialize Massive.com: {e}"))
            self.stdout.write("\n💡 Make sure MASSIVE_API_KEY is set in your environment")
            return

        if tickers:
            funds = Fund.objects.filter(ticker__in=tickers, is_active=True)
        else:
            funds = Fund.objects.filter(is_active=True)

        if not funds.exists():
            self.stdout.write(self.style.WARNING("⚠️  No active funds found to update"))
            return

        self.stdout.write(f"📊 Updating {funds.count()} funds with last {days} day(s) of data\n")

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        success_count = 0
        error_count = 0
        skipped_count = 0

        for fund in funds:
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

                created_count = 0
                updated_count = 0

                for perf_dto in performance_data:
                    performance, created = FundPerformance.objects.update_or_create(
                        asset=fund,
                        date=perf_dto.date,
                        defaults={
                            "open_price": perf_dto.open_price,
                            "high_price": perf_dto.high_price,
                            "low_price": perf_dto.low_price,
                            "close_price": perf_dto.close_price,
                            "adjusted_close": perf_dto.adjusted_close,
                            "volume": perf_dto.volume,
                            "dividend": perf_dto.dividend,
                            "split_ratio": perf_dto.split_ratio,
                        },
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                latest_price = performance_data[-1].close_price
                fund.previous_value = fund.current_value
                fund.current_value = latest_price
                fund.last_price_update = timezone.now()
                fund.save(update_fields=["previous_value", "current_value", "last_price_update"])

                sync_record.records_fetched = len(performance_data)
                sync_record.records_created = created_count
                sync_record.records_updated = updated_count
                sync_record.mark_complete(success=True)

                self.stdout.write(self.style.SUCCESS(f"✅ {fund.ticker}: {created_count} new, {updated_count} updated"))
                success_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ {fund.ticker}: {e}"))
                error_count += 1
                if "sync_record" in locals():
                    sync_record.mark_complete(success=False, error_message=str(e))

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"✅ Successfully updated: {success_count}")
        if skipped_count > 0:
            self.stdout.write(f"⏭️  Skipped (up-to-date): {skipped_count}")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"❌ Failed: {error_count}"))
        self.stdout.write(f"{'='*60}\n")
