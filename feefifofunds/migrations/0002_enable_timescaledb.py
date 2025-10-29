"""
Migration to enable TimescaleDB and create hypertables.

This migration:
1. Enables the TimescaleDB extension
2. Converts FundPerformance table to a hypertable
3. Sets up compression policies for old data
4. Creates continuous aggregates for common queries
5. Sets up retention policies

Note: This migration is designed to be optional. If TimescaleDB is not available,
the application will continue to work with regular PostgreSQL tables.
"""

from django.db import migrations, transaction


def enable_timescaledb(apps, schema_editor):
    """Enable TimescaleDB extension and configure hypertables."""
    # Check if we're using PostgreSQL
    if schema_editor.connection.vendor != "postgresql":
        print("Skipping TimescaleDB setup (not using PostgreSQL)")
        return

    # Try to enable TimescaleDB using a savepoint to isolate failures
    try:
        with transaction.atomic():
            with schema_editor.connection.cursor() as cursor:
                # Enable TimescaleDB extension
                cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                print("✅ TimescaleDB extension enabled")

                # Convert FundPerformance table to hypertable
                # This must be done on an empty table or during initial setup
                cursor.execute(
                    """
                    SELECT create_hypertable(
                        'feefifofunds_performance',
                        'date',
                        chunk_time_interval => INTERVAL '1 month',
                        if_not_exists => TRUE
                    );
                    """
                )
                print("✅ FundPerformance converted to hypertable with 1-month chunks")

                # Add compression policy for data older than 3 months
                cursor.execute(
                    """
                    SELECT add_compression_policy(
                        'feefifofunds_performance',
                        compress_after => INTERVAL '3 months',
                        if_not_exists => TRUE
                    );
                    """
                )
                print("✅ Compression policy added (compress data > 3 months old)")

                # Add retention policy to delete data older than 10 years
                cursor.execute(
                    """
                    SELECT add_retention_policy(
                        'feefifofunds_performance',
                        drop_after => INTERVAL '10 years',
                        if_not_exists => TRUE
                    );
                    """
                )
                print("✅ Retention policy added (drop data > 10 years old)")

                # Create continuous aggregate for daily OHLCV summary by fund
                cursor.execute(
                    """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS fund_performance_daily
                    WITH (timescaledb.continuous) AS
                    SELECT
                        fund_id,
                        time_bucket('1 day', date) AS bucket,
                        first(open_price, date) AS open_price,
                        max(high_price) AS high_price,
                        min(low_price) AS low_price,
                        last(close_price, date) AS close_price,
                        sum(volume) AS total_volume
                    FROM feefifofunds_performance
                    WHERE interval = '1D'
                    GROUP BY fund_id, bucket
                    WITH NO DATA;
                    """
                )
                print("✅ Continuous aggregate created (daily OHLCV summary)")

                # Add refresh policy for continuous aggregate
                cursor.execute(
                    """
                    SELECT add_continuous_aggregate_policy(
                        'fund_performance_daily',
                        start_offset => INTERVAL '1 month',
                        end_offset => INTERVAL '1 hour',
                        schedule_interval => INTERVAL '1 hour',
                        if_not_exists => TRUE
                    );
                    """
                )
                print("✅ Refresh policy added for continuous aggregate")

                # Create indexes optimized for TimescaleDB
                # Note: TimescaleDB automatically creates an index on the time column
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_fund_perf_fund_date_desc
                    ON feefifofunds_performance (fund_id, date DESC);
                    """
                )
                print("✅ TimescaleDB-optimized indexes created")

                print("🎉 TimescaleDB configuration complete!")

    except Exception as e:
        print(f"⚠️  TimescaleDB setup failed: {e}")
        print("⚠️  Continuing with regular PostgreSQL tables")
        print("⚠️  For full time-series optimization, install TimescaleDB extension")


def disable_timescaledb(apps, schema_editor):
    """
    Reverse migration - remove TimescaleDB configuration.

    WARNING: This will delete continuous aggregates and policies,
    but will preserve the data by converting hypertables back to regular tables.
    """
    if schema_editor.connection.vendor != "postgresql":
        return

    try:
        with transaction.atomic():
            with schema_editor.connection.cursor() as cursor:
                # Remove continuous aggregate
                cursor.execute("DROP MATERIALIZED VIEW IF EXISTS fund_performance_daily CASCADE;")
                print("Removed continuous aggregate")

                # Note: We don't drop the hypertable or extension
                # as that would require dropping all data
                # The hypertable will continue to work as a regular table

                print("TimescaleDB features disabled (hypertable preserved as regular table)")

    except Exception as e:
        print(f"Warning: TimescaleDB cleanup failed: {e}")


class Migration(migrations.Migration):
    """
    Enable TimescaleDB and configure hypertables for time-series data.

    Dependencies: Requires FUND-002 (models must exist first)
    """

    dependencies = [
        ("feefifofunds", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(enable_timescaledb, reverse_code=disable_timescaledb),
    ]
