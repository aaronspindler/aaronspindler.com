"""
Management command to fetch fund data from external sources.

CURRENTLY DISABLED: External data sources are not implemented.
Use Django admin to add funds manually.

Future usage (when data sources are implemented):
    python manage.py fetch_fund SPY --source alpha_vantage
    python manage.py fetch_fund SPY --historical --days 365
    python manage.py fetch_fund SPY --holdings
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Fetch fund data from external sources."""

    help = "Fetch fund data from external sources (currently disabled)"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("ticker", type=str, help="Fund ticker symbol (e.g., SPY, VTSAX)")

        parser.add_argument(
            "--source",
            type=str,
            default="none",
            choices=["none"],
            help="Data source to use (none available)",
        )

        parser.add_argument("--info", action="store_true", help="Fetch fund information only")

        parser.add_argument("--historical", action="store_true", help="Fetch historical price data")

        parser.add_argument("--days", type=int, default=365, help="Number of days of historical data (default: 365)")

        parser.add_argument("--holdings", action="store_true", help="Fetch fund holdings")

        parser.add_argument("--save", action="store_true", help="Save data to database")

        parser.add_argument("--all", action="store_true", help="Fetch all data types")

    def handle(self, *args, **options):
        """Execute the command."""
        # Show helpful error message
        self.stdout.write(self.style.ERROR("\n❌ External data sources are not currently implemented\n"))
        self.stdout.write("\n📋 How to add fund data:\n")
        self.stdout.write("  1. Use Django admin: http://localhost:8000/admin/feefifofunds/fund/add/")
        self.stdout.write("  2. Add funds manually with all required fields")
        self.stdout.write("  3. Add performance data via admin if needed")
        self.stdout.write("  4. Or use: python manage.py add_sample_funds\n")
        self.stdout.write("\n🔮 Future data sources (planned):")
        self.stdout.write("  - Alpha Vantage (official API, free tier)")
        self.stdout.write("  - Polygon.io (official API, free tier)")
        self.stdout.write("  - Finnhub (official API, free tier)")
        self.stdout.write("  - CSV import for bulk data\n")
