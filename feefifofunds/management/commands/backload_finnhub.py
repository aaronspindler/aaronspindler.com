"""
Management command to backload historical data from Finnhub.

Usage:
    python manage.py backload_finnhub SPY --days 365
    python manage.py backload_finnhub SPY QQQ VOO --days 180
    python manage.py backload_finnhub --all --days 365
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from feefifofunds.models import DataSync, Fund
from feefifofunds.models.performance import FundPerformance
from feefifofunds.services.data_sources.finnhub import FinnhubDataSource


class Command(BaseCommand):
    help = "Backload historical price data from Finnhub"

    def add_arguments(self, parser):
        parser.add_argument("tickers", nargs="*", type=str, help="Fund ticker symbols (e.g., SPY, QQQ)")

        parser.add_argument(
            "--all",
            action="store_true",
            help="Backload data for all existing funds in database",
        )

        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Number of days of historical data to fetch (default: 365, max: 365 for free tier)",
        )

        parser.add_argument(
            "--create-fund",
            action="store_true",
            help="Create fund if it doesn't exist",
        )

        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip performance data that already exists",
        )

    def handle(self, *args, **options):
        tickers = options["tickers"]
        fetch_all = options["all"]
        days = min(options["days"], 365)
        create_fund = options["create_fund"]
        skip_existing = options["skip_existing"]

        if not tickers and not fetch_all:
            self.stdout.write(self.style.ERROR("❌ Please provide ticker symbols or use --all flag"))
            return

        try:
            data_source = FinnhubDataSource()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to initialize Finnhub: {e}"))
            self.stdout.write("\n💡 Make sure FINNHUB_API_KEY is set in your environment")
            return

        if fetch_all:
            funds = Fund.objects.filter(is_active=True)
            tickers = [fund.ticker for fund in funds]
            self.stdout.write(f"📊 Backloading data for {len(tickers)} funds")
        else:
            self.stdout.write(f"📊 Backloading data for: {', '.join(tickers)}")

        self.stdout.write(f"📅 Fetching {days} days of historical data\n")

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        success_count = 0
        error_count = 0

        for ticker in tickers:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Processing {ticker}...")
            self.stdout.write(f"{'='*60}")

            try:
                fund = Fund.objects.filter(ticker=ticker).first()

                if not fund:
                    if create_fund:
                        self.stdout.write(f"🔍 Fetching fund info for {ticker}...")
                        fund_info = data_source.fetch_fund_info(ticker)
                        fund = Fund.objects.create(
                            ticker=fund_info.ticker,
                            name=fund_info.name,
                            description=fund_info.description or "",
                            exchange=fund_info.exchange or "",
                            current_value=fund_info.current_price,
                            previous_value=fund_info.previous_close,
                            quote_currency=fund_info.currency,
                            isin=fund_info.isin,
                            website=fund_info.website or "",
                            aum=fund_info.aum,
                        )
                        self.stdout.write(self.style.SUCCESS(f"✅ Created fund: {fund}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"❌ Fund {ticker} not found. Use --create-fund to create."))
                        error_count += 1
                        continue

                sync_record = data_source.create_sync_record(
                    sync_type=DataSync.SyncType.PRICES,
                    fund=fund,
                    request_params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                )

                self.stdout.write(f"📥 Fetching historical data from {start_date} to {end_date}...")
                performance_data = data_source.fetch_historical_prices(ticker, start_date, end_date)

                self.stdout.write(f"💾 Saving {len(performance_data)} records...")

                created_count = 0
                updated_count = 0
                skipped_count = 0

                for perf_dto in performance_data:
                    if skip_existing:
                        existing = FundPerformance.objects.filter(asset=fund, date=perf_dto.date).exists()
                        if existing:
                            skipped_count += 1
                            continue

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

                fund.current_value = performance_data[-1].close_price if performance_data else fund.current_value
                fund.last_price_update = timezone.now()
                fund.save(update_fields=["current_value", "last_price_update"])

                sync_record.records_fetched = len(performance_data)
                sync_record.records_created = created_count
                sync_record.records_updated = updated_count
                sync_record.mark_complete(success=True)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {ticker}: {created_count} created, {updated_count} updated, {skipped_count} skipped"
                    )
                )
                success_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error processing {ticker}: {e}"))
                error_count += 1
                if "sync_record" in locals():
                    sync_record.mark_complete(success=False, error_message=str(e))

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"✅ Successfully processed: {success_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"❌ Failed: {error_count}"))
        self.stdout.write(f"{'='*60}\n")
