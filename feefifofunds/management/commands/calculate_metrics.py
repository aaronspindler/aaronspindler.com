"""
Management command to calculate financial metrics for funds.

Usage:
    python manage.py calculate_metrics SPY
    python manage.py calculate_metrics SPY --timeframe 3Y
    python manage.py calculate_metrics --all
"""

from django.core.management.base import BaseCommand, CommandError

from feefifofunds.models import Fund
from feefifofunds.services.calculators import MetricsCalculator


class Command(BaseCommand):
    """Calculate financial metrics for funds."""

    help = "Calculate financial metrics for funds"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("ticker", nargs="?", type=str, help="Fund ticker symbol (e.g., SPY)")

        parser.add_argument("--all", action="store_true", help="Calculate metrics for all active funds")

        parser.add_argument(
            "--timeframe",
            type=str,
            default="1Y",
            choices=["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "10Y", "ALL"],
            help="Time frame for calculations (default: 1Y)",
        )

        parser.add_argument("--all-timeframes", action="store_true", help="Calculate for all time frames")

    def handle(self, *args, **options):
        """Execute the command."""
        ticker = options.get("ticker")
        calculate_all = options["all"]
        timeframe = options["timeframe"]
        all_timeframes = options["all_timeframes"]

        if not ticker and not calculate_all:
            raise CommandError("Please provide a ticker or use --all")

        # Get funds to process
        if calculate_all:
            funds = Fund.objects.filter(is_active=True)
            self.stdout.write(f"\n📊 Calculating metrics for {funds.count()} funds\n")
        else:
            funds = Fund.objects.filter(ticker=ticker.upper(), is_active=True)
            if not funds.exists():
                raise CommandError(f"Fund {ticker} not found")

        # Time frames to calculate
        if all_timeframes:
            timeframes = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "10Y"]
        else:
            timeframes = [timeframe]

        # Process each fund
        total_calculated = 0
        for fund in funds:
            self.stdout.write(f"\n{fund.ticker} - {fund.name}")

            calculator = MetricsCalculator(fund)

            for tf in timeframes:
                self.stdout.write(f"  Calculating {tf} metrics...")

                try:
                    metrics = calculator.calculate_all_metrics(time_frame=tf)

                    if metrics:
                        self.stdout.write(self.style.SUCCESS(f"  ✅ {tf}:"))
                        if metrics.total_return is not None:
                            self.stdout.write(f"     Total Return: {metrics.total_return:.2f}%")
                        if metrics.annualized_return is not None:
                            self.stdout.write(f"     Annualized Return: {metrics.annualized_return:.2f}%")
                        if metrics.volatility is not None:
                            self.stdout.write(f"     Volatility: {metrics.volatility:.2f}%")
                        self.stdout.write(f"     Data Points: {metrics.data_points}")

                        total_calculated += 1
                    else:
                        self.stdout.write(self.style.WARNING(f"  ⚠️  {tf}: Not enough data"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ {tf}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n✅ Calculated {total_calculated} metrics\n"))
