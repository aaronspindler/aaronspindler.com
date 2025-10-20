"""
Management command to fetch fund data from external sources.

Usage:
    python manage.py fetch_fund SPY --source yahoo_finance
    python manage.py fetch_fund SPY --historical --days 365
    python manage.py fetch_fund SPY --holdings
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from feefifofunds.models import Fund, FundHolding, FundPerformance
from feefifofunds.services.data_sources.yahoo_finance import YahooFinance


class Command(BaseCommand):
    """Fetch fund data from external sources."""

    help = "Fetch fund data from external sources (Yahoo Finance, Alpha Vantage, etc.)"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("ticker", type=str, help="Fund ticker symbol (e.g., SPY, VTSAX)")

        parser.add_argument(
            "--source",
            type=str,
            default="yahoo_finance",
            choices=["yahoo_finance"],
            help="Data source to use (default: yahoo_finance)",
        )

        parser.add_argument("--info", action="store_true", help="Fetch fund information only")

        parser.add_argument("--historical", action="store_true", help="Fetch historical price data")

        parser.add_argument("--days", type=int, default=365, help="Number of days of historical data (default: 365)")

        parser.add_argument("--holdings", action="store_true", help="Fetch fund holdings")

        parser.add_argument("--save", action="store_true", help="Save data to database")

        parser.add_argument("--all", action="store_true", help="Fetch all data types")

    def handle(self, *args, **options):
        """Execute the command."""
        ticker = options["ticker"].upper()
        source_name = options["source"]

        self.stdout.write(self.style.SUCCESS(f"\n📊 Fetching data for {ticker} from {source_name}\n"))

        # Initialize data source
        if source_name == "yahoo_finance":
            source = YahooFinance()
        else:
            raise CommandError(f"Unsupported data source: {source_name}")

        # Determine what to fetch
        fetch_info = options["info"] or options["all"]
        fetch_historical = options["historical"] or options["all"]
        fetch_holdings = options["holdings"] or options["all"]

        # Default: fetch info if nothing specified
        if not (fetch_info or fetch_historical or fetch_holdings):
            fetch_info = True

        # Fetch fund info
        if fetch_info:
            self.stdout.write("📋 Fetching fund information...")
            try:
                fund_data = source.fetch_fund_info(ticker)
                self.stdout.write(self.style.SUCCESS(f"✅ Fund: {fund_data.name}"))
                self.stdout.write(f"   Ticker: {fund_data.ticker}")
                self.stdout.write(f"   Type: {fund_data.fund_type}")
                self.stdout.write(f"   Asset Class: {fund_data.asset_class}")
                self.stdout.write(f"   Expense Ratio: {fund_data.expense_ratio}%")
                self.stdout.write(f"   Current Price: ${fund_data.current_price}")
                self.stdout.write(f"   AUM: ${fund_data.aum}M")

                if options["save"]:
                    # Create or update fund
                    fund, created = Fund.objects.update_or_create(
                        ticker=fund_data.ticker,
                        defaults={
                            "name": fund_data.name,
                            "fund_type": fund_data.fund_type,
                            "asset_class": fund_data.asset_class,
                            "category": fund_data.category,
                            "description": fund_data.description,
                            "inception_date": fund_data.inception_date,
                            "issuer": fund_data.issuer,
                            "expense_ratio": fund_data.expense_ratio,
                            "management_fee": fund_data.management_fee,
                            "current_price": fund_data.current_price,
                            "previous_close": fund_data.previous_close,
                            "currency": fund_data.currency,
                            "aum": fund_data.aum,
                            "avg_volume": fund_data.avg_volume,
                            "exchange": fund_data.exchange,
                            "website": fund_data.website,
                            "isin": fund_data.isin,
                            "last_updated": fund_data.fetched_at,
                        },
                    )
                    action = "Created" if created else "Updated"
                    self.stdout.write(self.style.SUCCESS(f"   {action} fund in database"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Failed to fetch fund info: {e}"))

        # Fetch historical prices
        if fetch_historical:
            days = options["days"]
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            self.stdout.write(f"\n📈 Fetching {days} days of historical prices...")
            self.stdout.write(f"   Period: {start_date} to {end_date}")

            try:
                prices = source.fetch_historical_prices(ticker, start_date, end_date)
                self.stdout.write(self.style.SUCCESS(f"✅ Fetched {len(prices)} price records"))

                if prices:
                    first = prices[0]
                    last = prices[-1]
                    self.stdout.write(f"   First: {first.date} - ${first.close_price}")
                    self.stdout.write(f"   Last: {last.date} - ${last.close_price}")

                    if options["save"]:
                        # Get or create fund
                        fund = Fund.objects.filter(ticker=ticker).first()
                        if not fund:
                            self.stdout.write(
                                self.style.WARNING("   Fund not in database, run with --info --save first")
                            )
                        else:
                            # Save performance data
                            created_count = 0
                            updated_count = 0
                            for perf in prices:
                                _, created = FundPerformance.objects.update_or_create(
                                    fund=fund,
                                    date=perf.date,
                                    interval=perf.interval,
                                    defaults={
                                        "open_price": perf.open_price,
                                        "high_price": perf.high_price,
                                        "low_price": perf.low_price,
                                        "close_price": perf.close_price,
                                        "adjusted_close": perf.adjusted_close,
                                        "volume": perf.volume,
                                        "dividend": perf.dividend,
                                        "split_ratio": perf.split_ratio,
                                        "data_source": perf.source,
                                    },
                                )
                                if created:
                                    created_count += 1
                                else:
                                    updated_count += 1

                            self.stdout.write(
                                self.style.SUCCESS(f"   Created {created_count}, Updated {updated_count} records")
                            )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Failed to fetch historical prices: {e}"))

        # Fetch holdings
        if fetch_holdings:
            self.stdout.write("\n🏦 Fetching fund holdings...")

            try:
                holdings = source.fetch_holdings(ticker)
                self.stdout.write(self.style.SUCCESS(f"✅ Fetched {len(holdings)} holdings"))

                if holdings:
                    self.stdout.write("\n   Top 5 holdings:")
                    for holding in holdings[:5]:
                        self.stdout.write(f"   - {holding.ticker}: {holding.name} ({holding.weight}%)")

                    if options["save"]:
                        fund = Fund.objects.filter(ticker=ticker).first()
                        if not fund:
                            self.stdout.write(
                                self.style.WARNING("   Fund not in database, run with --info --save first")
                            )
                        else:
                            # Save holdings
                            created_count = 0
                            for holding in holdings:
                                _, created = FundHolding.objects.update_or_create(
                                    fund=fund,
                                    ticker=holding.ticker,
                                    as_of_date=holding.as_of_date or date.today(),
                                    defaults={
                                        "name": holding.name,
                                        "weight": holding.weight,
                                        "shares": holding.shares,
                                        "market_value": holding.market_value,
                                        "holding_type": holding.holding_type,
                                        "sector": holding.sector,
                                        "industry": holding.industry,
                                        "country": holding.country,
                                        "cusip": holding.cusip,
                                        "isin": holding.isin,
                                        "data_source": holding.source,
                                    },
                                )
                                if created:
                                    created_count += 1

                            self.stdout.write(self.style.SUCCESS(f"   Created/Updated {created_count} holdings"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Failed to fetch holdings: {e}"))

        self.stdout.write(self.style.SUCCESS("\n✅ Fetch complete!\n"))
