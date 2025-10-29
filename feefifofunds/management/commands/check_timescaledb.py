"""
Management command to check TimescaleDB status and configuration.

Usage:
    python manage.py check_timescaledb
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    """Check TimescaleDB installation and configuration."""

    help = "Check TimescaleDB status and configuration"

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write(self.style.SUCCESS("\n🔍 Checking TimescaleDB Status\n"))

        with connection.cursor() as cursor:
            # Check if TimescaleDB extension is installed
            cursor.execute(
                """
                SELECT extname, extversion
                FROM pg_extension
                WHERE extname = 'timescaledb';
                """
            )
            result = cursor.fetchone()

            if result:
                self.stdout.write(self.style.SUCCESS(f"✅ TimescaleDB extension installed: {result[0]} v{result[1]}"))
            else:
                self.stdout.write(self.style.WARNING("⚠️  TimescaleDB extension not installed"))
                self.stdout.write(
                    self.style.WARNING("   Application will use regular PostgreSQL (slower for time-series queries)")
                )
                return

            # Check hypertables
            cursor.execute(
                """
                SELECT hypertable_name, num_chunks, compression_enabled
                FROM timescaledb_information.hypertables
                WHERE hypertable_schema = 'public';
                """
            )
            hypertables = cursor.fetchall()

            if hypertables:
                self.stdout.write(self.style.SUCCESS(f"\n✅ Found {len(hypertables)} hypertable(s):"))
                for table, chunks, compression in hypertables:
                    comp_status = "enabled" if compression else "disabled"
                    self.stdout.write(f"   - {table}: {chunks} chunks, compression {comp_status}")
            else:
                self.stdout.write(self.style.WARNING("\n⚠️  No hypertables configured"))
                self.stdout.write(
                    self.style.WARNING("   Run migrations to convert tables to hypertables: python manage.py migrate")
                )

            # Check continuous aggregates
            cursor.execute(
                """
                SELECT view_name, materialization_hypertable_name
                FROM timescaledb_information.continuous_aggregates;
                """
            )
            aggregates = cursor.fetchall()

            if aggregates:
                self.stdout.write(self.style.SUCCESS(f"\n✅ Found {len(aggregates)} continuous aggregate(s):"))
                for view_name, mat_table in aggregates:
                    self.stdout.write(f"   - {view_name} → {mat_table}")
            else:
                self.stdout.write(self.style.WARNING("\n⚠️  No continuous aggregates configured"))

            # Check compression statistics
            cursor.execute(
                """
                SELECT
                    hypertable_name,
                    total_chunks,
                    number_compressed_chunks,
                    uncompressed_heap_bytes,
                    compressed_heap_bytes,
                    CASE
                        WHEN uncompressed_heap_bytes > 0 THEN
                            ROUND(100.0 * compressed_heap_bytes / uncompressed_heap_bytes, 2)
                        ELSE 0
                    END AS compression_ratio
                FROM timescaledb_information.compression_settings
                WHERE hypertable_schema = 'public';
                """
            )
            compression_stats = cursor.fetchall()

            if compression_stats:
                self.stdout.write(self.style.SUCCESS("\n✅ Compression Statistics:"))
                for table, total, compressed, uncompressed, compressed_size, ratio in compression_stats:
                    self.stdout.write(f"   - {table}:")
                    self.stdout.write(f"     Total chunks: {total}")
                    self.stdout.write(f"     Compressed chunks: {compressed}")
                    self.stdout.write(f"     Compression ratio: {ratio}%")

            # Check policies
            cursor.execute(
                """
                SELECT
                    hypertable_name,
                    policy_type,
                    config
                FROM timescaledb_information.jobs
                WHERE application_name LIKE 'Compression Policy%'
                   OR application_name LIKE 'Retention Policy%'
                   OR application_name LIKE 'Refresh Continuous Aggregate%';
                """
            )
            policies = cursor.fetchall()

            if policies:
                self.stdout.write(self.style.SUCCESS(f"\n✅ Found {len(policies)} active policies"))
            else:
                self.stdout.write(self.style.WARNING("\n⚠️  No policies configured"))

            # Show table sizes
            cursor.execute(
                """
                SELECT
                    hypertable_name,
                    pg_size_pretty(hypertable_size(format('%I.%I', hypertable_schema, hypertable_name)::regclass))
                        AS total_size
                FROM timescaledb_information.hypertables
                WHERE hypertable_schema = 'public';
                """
            )
            sizes = cursor.fetchall()

            if sizes:
                self.stdout.write(self.style.SUCCESS("\n📊 Hypertable Sizes:"))
                for table, size in sizes:
                    self.stdout.write(f"   - {table}: {size}")

        self.stdout.write(self.style.SUCCESS("\n✅ TimescaleDB check complete!\n"))
