from django.core.management.base import BaseCommand, CommandError

from feefifofunds.models import Asset


class Command(BaseCommand):
    help = "Create a new asset in the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ticker",
            type=str,
            required=True,
            help="Asset ticker symbol (e.g., BTC, AAPL, GLD)",
        )
        parser.add_argument(
            "--name",
            type=str,
            required=True,
            help="Full asset name",
        )
        parser.add_argument(
            "--category",
            type=str,
            required=True,
            choices=["STOCK", "CRYPTO", "COMMODITY", "CURRENCY"],
            help="Asset category",
        )
        parser.add_argument(
            "--quote-currency",
            type=str,
            default="USD",
            help="Currency for pricing (default: USD)",
        )
        parser.add_argument(
            "--description",
            type=str,
            default="",
            help="Optional asset description",
        )

    def handle(self, *args, **options):
        ticker = options["ticker"].upper()
        name = options["name"]
        category = options["category"]
        quote_currency = options["quote_currency"].upper()
        description = options["description"]

        if Asset.objects.filter(ticker=ticker).exists():
            raise CommandError(f"Asset with ticker '{ticker}' already exists")

        asset = Asset.objects.create(
            ticker=ticker,
            name=name,
            category=category,
            quote_currency=quote_currency,
            description=description,
            active=True,
        )

        self.stdout.write(self.style.SUCCESS(f"✓ Created asset: {asset.ticker} - {asset.name}"))
        self.stdout.write(f"  Category: {asset.get_category_display()}")
        self.stdout.write(f"  Quote Currency: {asset.quote_currency}")
