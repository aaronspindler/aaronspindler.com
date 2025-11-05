from django.core.management.base import BaseCommand

from feefifofunds.models import Fund

from .massive_utils import (
    get_date_range,
    handle_sync_error,
    initialize_data_source,
    process_fund_creation,
    save_performance_data,
)


class Command(BaseCommand):
    help = "Backload historical price data from Massive.com"

    def add_arguments(self, parser) -> None:
        parser.add_argument("tickers", nargs="*", type=str, help="Fund ticker symbols (e.g., SPY, QQQ)")

        parser.add_argument(
            "--all",
            action="store_true",
            help="Backload data for all existing funds in database",
        )

        parser.add_argument(
            "--days",
            type=int,
            default=730,
            help="Number of days of historical data to fetch (default: 730, max: 730 for free tier)",
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

    def handle(self, *args, **options) -> None:
        tickers = options["tickers"]
        fetch_all = options["all"]
        days = options["days"]
        create_fund = options["create_fund"]
        skip_existing = options["skip_existing"]

        if not tickers and not fetch_all:
            self.stdout.write(self.style.ERROR("❌ Please provide ticker symbols or use --all flag"))
            return

        data_source = initialize_data_source(self.stdout, self.style)
        if data_source is None:
            return

        if fetch_all:
            funds = Fund.objects.filter(is_active=True)
            tickers = [fund.ticker for fund in funds]
            self.stdout.write(f"📊 Backloading data for {len(tickers)} funds")
        else:
            self.stdout.write(f"📊 Backloading data for: {', '.join(tickers)}")

        self.stdout.write(f"📅 Fetching {days} days of historical data (up to 2 years on free tier)\n")

        start_date, end_date = get_date_range(days)

        success_count = 0
        error_count = 0

        for ticker in tickers:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Processing {ticker}...")
            self.stdout.write(f"{'='*60}")

            sync_record = None

            try:
                fund = Fund.objects.filter(ticker=ticker).first()

                if not fund:
                    if create_fund:
                        fund = process_fund_creation(data_source, ticker, self.stdout, self.style)
                    else:
                        self.stdout.write(self.style.ERROR(f"❌ Fund {ticker} not found. Use --create-fund to create."))
                        error_count += 1
                        continue

                self.stdout.write(f"📥 Fetching historical data from {start_date} to {end_date}...")
                performance_data = data_source.fetch_historical_prices(ticker, start_date, end_date)

                self.stdout.write(f"💾 Saving {len(performance_data)} records...")

                created_count, updated_count, skipped_count, sync_record = save_performance_data(
                    fund=fund,
                    performance_data=performance_data,
                    data_source=data_source,
                    start_date=start_date,
                    end_date=end_date,
                    skip_existing=skip_existing,
                    stdout=self.stdout,
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {ticker}: {created_count} created, {updated_count} updated, {skipped_count} skipped"
                    )
                )
                success_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error processing {ticker}: {e}"))
                error_count += 1
                handle_sync_error(sync_record, str(e))

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"✅ Successfully processed: {success_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"❌ Failed: {error_count}"))
        self.stdout.write(f"{'='*60}\n")
