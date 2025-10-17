"""
Management command to import funds from CSV file.

Usage:
    python manage.py import_funds_csv funds.csv
    python manage.py import_funds_csv funds.csv --dry-run
    python manage.py import_funds_csv --generate-sample sample_funds.csv
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from feefifofunds.data_sources import CSVSource, DataSourceManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import fund data from CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", nargs="?", type=str, help="Path to CSV file to import")

        parser.add_argument(
            "--generate-sample", type=str, help="Generate a sample CSV file at the specified path", default=None
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Load and validate CSV but don't save to database",
        )

        parser.add_argument(
            "--update-existing",
            action="store_true",
            default=True,
            help="Update existing funds (default: True)",
        )

    def handle(self, *args, **options):
        # Generate sample CSV if requested
        if options["generate_sample"]:
            output_path = options["generate_sample"]
            try:
                CSVSource.generate_sample_csv(output_path)
                self.stdout.write(self.style.SUCCESS(f"✓ Generated sample CSV at: {output_path}"))
                self.stdout.write("\nSample CSV contains 3 example funds:")
                self.stdout.write("  1. VFV.TO - Vanguard S&P 500 ETF (MER: 0.08%)")
                self.stdout.write("  2. TDB902 - TD U.S. Index Fund (MER: 0.35%)")
                self.stdout.write("  3. RBF556 - RBC Select Balanced (MER: 2.04%)")
                return
            except Exception as e:
                raise CommandError(f"Error generating sample CSV: {e}")

        # Import CSV file
        csv_file = options["csv_file"]
        if not csv_file:
            raise CommandError(
                "No CSV file provided. Use: python manage.py import_funds_csv <file.csv>\n"
                "Or generate a sample: python manage.py import_funds_csv --generate-sample sample.csv"
            )

        dry_run = options["dry_run"]
        update_existing = options["update_existing"]

        self.stdout.write(f"Importing funds from: {csv_file}")

        try:
            # Load CSV
            csv_source = CSVSource(csv_path=csv_file)
            funds_data = csv_source.load_csv(csv_file)

            if not funds_data:
                self.stdout.write(self.style.WARNING("⚠ No funds found in CSV"))
                return

            self.stdout.write(f"\nLoaded {len(funds_data)} fund(s) from CSV")

            # Display funds
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("FUNDS TO IMPORT")
            self.stdout.write("=" * 60)

            for i, fund_data in enumerate(funds_data, 1):
                self.stdout.write(f"\n{i}. {fund_data.ticker} - {fund_data.name}")
                self.stdout.write(f"   Type: {fund_data.fund_type}, MER: {fund_data.mer}%")
                self.stdout.write(f"   Provider: {fund_data.provider_name}")
                self.stdout.write(f"   Complete: {fund_data.is_complete()}")

            if dry_run:
                self.stdout.write("\n" + "=" * 60)
                self.stdout.write(self.style.WARNING("⚠ DRY RUN MODE: No changes will be saved"))
                self.stdout.write("=" * 60)
                return

            # Save to database
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("IMPORTING TO DATABASE")
            self.stdout.write("=" * 60)

            manager = DataSourceManager()

            success_count = 0
            skip_count = 0
            error_count = 0

            for fund_data in funds_data:
                try:
                    if not fund_data.is_complete():
                        self.stdout.write(
                            self.style.WARNING(f"⚠ Skipping {fund_data.ticker}: incomplete data (missing MER)")
                        )
                        skip_count += 1
                        continue

                    fund = manager.save_to_db(fund_data, update_existing=update_existing)

                    if fund:
                        self.stdout.write(self.style.SUCCESS(f"✓ Saved {fund.ticker} - {fund.name} (ID: {fund.id})"))
                        success_count += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"⚠ Skipped {fund_data.ticker} (already exists, not updated)")
                        )
                        skip_count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Error saving {fund_data.ticker}: {e}"))
                    logger.exception(f"Error importing {fund_data.ticker}")
                    error_count += 1
                    continue

            # Summary
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("IMPORT SUMMARY"))
            self.stdout.write("=" * 60)
            self.stdout.write(f"Total funds in CSV: {len(funds_data)}")
            self.stdout.write(self.style.SUCCESS(f"✓ Successfully imported: {success_count}"))
            self.stdout.write(self.style.WARNING(f"⚠ Skipped: {skip_count}"))
            self.stdout.write(self.style.ERROR(f"✗ Errors: {error_count}"))

        except FileNotFoundError:
            raise CommandError(f"CSV file not found: {csv_file}")
        except ValueError as e:
            raise CommandError(f"Invalid CSV format: {e}")
        except Exception as e:
            raise CommandError(f"Error importing CSV: {e}")
