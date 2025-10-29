"""
Management command to add sample fund data for testing.

This creates a few popular ETFs with basic information for testing
the FeeFiFoFunds interface without requiring external data sources.

Usage:
    python manage.py add_sample_funds
    python manage.py add_sample_funds --clear  # Clear existing first
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from feefifofunds.models import Fund


class Command(BaseCommand):
    """Add sample fund data for testing."""

    help = "Add sample fund data for testing the interface"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("--clear", action="store_true", help="Clear existing funds before adding samples")

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write(self.style.SUCCESS("\n📊 Adding sample fund data\n"))

        if options["clear"]:
            count = Fund.objects.count()
            Fund.objects.all().delete(soft=False)  # Hard delete for clean slate
            self.stdout.write(self.style.WARNING(f"Cleared {count} existing funds\n"))

        # Sample funds data
        sample_funds = [
            {
                "ticker": "SPY",
                "name": "SPDR S&P 500 ETF Trust",
                "fund_type": "ETF",
                "asset_class": "EQUITY",
                "category": "Large Blend",
                "issuer": "State Street",
                "description": "Seeks to track the S&P 500 Index, which measures the performance of the large-cap segment of the U.S. equity market.",
                "inception_date": date(1993, 1, 22),
                "expense_ratio": Decimal("0.0945"),
                "current_price": Decimal("573.00"),
                "previous_close": Decimal("571.50"),
                "currency": "USD",
                "aum": Decimal("534000.00"),  # $534 billion
                "exchange": "NYSE Arca",
            },
            {
                "ticker": "VOO",
                "name": "Vanguard S&P 500 ETF",
                "fund_type": "ETF",
                "asset_class": "EQUITY",
                "category": "Large Blend",
                "issuer": "Vanguard",
                "description": "Seeks to track the performance of the S&P 500 Index.",
                "inception_date": date(2010, 9, 7),
                "expense_ratio": Decimal("0.03"),
                "current_price": Decimal("522.00"),
                "previous_close": Decimal("520.75"),
                "currency": "USD",
                "aum": Decimal("537000.00"),  # $537 billion
                "exchange": "NYSE Arca",
            },
            {
                "ticker": "QQQ",
                "name": "Invesco QQQ Trust",
                "fund_type": "ETF",
                "asset_class": "EQUITY",
                "category": "Large Growth",
                "issuer": "Invesco",
                "description": "Seeks to track the Nasdaq-100 Index, which includes the largest non-financial companies on the Nasdaq.",
                "inception_date": date(1999, 3, 10),
                "expense_ratio": Decimal("0.20"),
                "current_price": Decimal("502.00"),
                "previous_close": Decimal("499.25"),
                "currency": "USD",
                "aum": Decimal("306000.00"),  # $306 billion
                "exchange": "NASDAQ",
            },
            {
                "ticker": "VTI",
                "name": "Vanguard Total Stock Market ETF",
                "fund_type": "ETF",
                "asset_class": "EQUITY",
                "category": "Large Blend",
                "issuer": "Vanguard",
                "description": "Seeks to track the CRSP US Total Market Index, covering the entire U.S. equity market.",
                "inception_date": date(2001, 5, 24),
                "expense_ratio": Decimal("0.03"),
                "current_price": Decimal("286.00"),
                "previous_close": Decimal("285.00"),
                "currency": "USD",
                "aum": Decimal("456000.00"),  # $456 billion
                "exchange": "NYSE Arca",
            },
            {
                "ticker": "AGG",
                "name": "iShares Core U.S. Aggregate Bond ETF",
                "fund_type": "ETF",
                "asset_class": "FIXED_INCOME",
                "category": "Intermediate Core Bond",
                "issuer": "BlackRock",
                "description": "Seeks to track the Bloomberg U.S. Aggregate Bond Index, a broad measure of the U.S. investment-grade bond market.",
                "inception_date": date(2003, 9, 22),
                "expense_ratio": Decimal("0.03"),
                "current_price": Decimal("99.50"),
                "previous_close": Decimal("99.45"),
                "currency": "USD",
                "aum": Decimal("119000.00"),  # $119 billion
                "exchange": "NYSE Arca",
            },
        ]

        created_count = 0
        updated_count = 0

        for fund_data in sample_funds:
            fund, created = Fund.objects.update_or_create(ticker=fund_data["ticker"], defaults=fund_data)

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Created: {fund.ticker} - {fund.name}"))
            else:
                updated_count += 1
                self.stdout.write(f"   Updated: {fund.ticker} - {fund.name}")

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Added {created_count} new funds, updated {updated_count} existing funds\n")
        )
        self.stdout.write("View at: http://localhost:8000/feefifofunds/funds/\n")
        self.stdout.write("Admin: http://localhost:8000/admin/feefifofunds/fund/\n")
