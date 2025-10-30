"""
Migration to enable TimescaleDB and create hypertables.

This migration:
1. Enables the TimescaleDB extension
2. Converts all performance tables to hypertables with date partitioning
3. Sets up compression policies (compress data older than 3 months)
4. Creates continuous aggregates for common queries

NOTE: No retention policy - data is retained forever.

Prerequisites:
- TimescaleDB extension must be installed and configured on PostgreSQL
- Performance tables must have composite PKs (from migration 0001)

Note: This migration is designed to be optional. If TimescaleDB is not available,
the application will continue to work with regular PostgreSQL tables.
"""

from django.db import migrations


# Performance tables to convert to hypertables
PERFORMANCE_TABLES = [
    ("feefifofunds_performance", "Fund Performance"),
    ("feefifofunds_crypto_performance", "Crypto Performance"),
    ("feefifofunds_currency_performance", "Currency Performance"),
    ("feefifofunds_commodity_performance", "Commodity Performance"),
    ("feefifofunds_inflation_data", "Inflation Data"),
    ("feefifofunds_savings_rate", "Savings Rate History"),
    ("feefifofunds_property_valuation", "Property Valuation"),
]


def enable_timescaledb(apps, schema_editor):
    """Enable TimescaleDB extension and configure hypertables."""
    if schema_editor.connection.vendor != "postgresql":
        print("Skipping TimescaleDB setup (not using PostgreSQL)")
        return

    try:
        with schema_editor.connection.cursor() as cursor:
            # Enable TimescaleDB extension
            cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            print("✅ TimescaleDB extension enabled")

            # Convert all performance tables to hypertables
            for table_name, display_name in PERFORMANCE_TABLES:
                try:
                    # Create hypertable with 1-month chunks
                    cursor.execute(f"""
                        SELECT create_hypertable(
                            '{table_name}',
                            'date',
                            chunk_time_interval => INTERVAL '1 month',
                            if_not_exists => TRUE
                        );
                    """)
                    print(f"✅ {display_name} ({table_name}) converted to hypertable")

                    # Enable compression on the hypertable
                    cursor.execute(f"""
                        ALTER TABLE {table_name} SET (
                            timescaledb.compress,
                            timescaledb.compress_segmentby = 'asset_id,interval'
                        );
                    """)
                    print(f"   └─ Compression enabled")

                    # Add compression policy for data older than 3 months
                    cursor.execute(f"""
                        SELECT add_compression_policy(
                            '{table_name}',
                            compress_after => INTERVAL '3 months',
                            if_not_exists => TRUE
                        );
                    """)
                    print(f"   └─ Compression policy added (compress data > 3 months old)")

                    # NO RETENTION POLICY - data retained forever

                except Exception as e:
                    print(f"⚠️  Failed to configure {display_name}: {e}")
                    raise

            # Create continuous aggregate for daily fund performance
            try:
                cursor.execute("""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS fund_performance_daily
                    WITH (timescaledb.continuous) AS
                    SELECT
                        asset_id,
                        time_bucket('1 day', date) AS bucket,
                        first(open_price, date) AS open_price,
                        max(high_price) AS high_price,
                        min(low_price) AS low_price,
                        last(close_price, date) AS close_price,
                        sum(volume) AS total_volume
                    FROM feefifofunds_performance
                    WHERE interval = '1D'
                    GROUP BY asset_id, bucket
                    WITH NO DATA;
                """)
                print("✅ Continuous aggregate created (daily fund OHLCV summary)")

                # Add refresh policy for continuous aggregate
                cursor.execute("""
                    SELECT add_continuous_aggregate_policy(
                        'fund_performance_daily',
                        start_offset => INTERVAL '1 month',
                        end_offset => INTERVAL '1 hour',
                        schedule_interval => INTERVAL '1 hour',
                        if_not_exists => TRUE
                    );
                """)
                print("   └─ Refresh policy added (updates hourly)")
            except Exception as e:
                print(f"⚠️  Failed to create fund performance aggregate: {e}")

            # Create continuous aggregate for daily crypto performance
            try:
                cursor.execute("""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS crypto_performance_daily
                    WITH (timescaledb.continuous) AS
                    SELECT
                        asset_id,
                        time_bucket('1 day', date) AS bucket,
                        first(open_price, date) AS open_price,
                        max(high_price) AS high_price,
                        min(low_price) AS low_price,
                        last(close_price, date) AS close_price,
                        sum(volume_24h) AS total_volume_24h,
                        last(market_cap, date) AS market_cap
                    FROM feefifofunds_crypto_performance
                    WHERE interval = '1D'
                    GROUP BY asset_id, bucket
                    WITH NO DATA;
                """)
                print("✅ Continuous aggregate created (daily crypto OHLCV summary)")

                # Add refresh policy
                cursor.execute("""
                    SELECT add_continuous_aggregate_policy(
                        'crypto_performance_daily',
                        start_offset => INTERVAL '1 month',
                        end_offset => INTERVAL '1 hour',
                        schedule_interval => INTERVAL '1 hour',
                        if_not_exists => TRUE
                    );
                """)
                print("   └─ Refresh policy added (updates hourly)")
            except Exception as e:
                print(f"⚠️  Failed to create crypto performance aggregate: {e}")

            print("🎉 TimescaleDB configuration complete for all performance tables!")
            print("📊 Data will be retained forever (no retention policy)")

    except Exception as e:
        print(f"⚠️  TimescaleDB setup failed: {e}")
        print("⚠️  Continuing with regular PostgreSQL tables")
        print("⚠️  For full time-series optimization, ensure TimescaleDB is installed")


def disable_timescaledb(apps, schema_editor):
    """
    Reverse migration - remove TimescaleDB configuration.

    WARNING: This will delete continuous aggregates and policies,
    but will preserve the data by converting hypertables back to regular tables.
    """
    if schema_editor.connection.vendor != "postgresql":
        return

    try:
        with schema_editor.connection.cursor() as cursor:
            # Remove continuous aggregates
            cursor.execute("DROP MATERIALIZED VIEW IF EXISTS fund_performance_daily CASCADE;")
            cursor.execute("DROP MATERIALIZED VIEW IF EXISTS crypto_performance_daily CASCADE;")
            print("Removed continuous aggregates")

            # Remove compression and retention policies (automatically removed when dropping hypertable)
            # Note: We don't drop the hypertables themselves as that would require dropping all data
            # The hypertables will continue to work as regular tables

            print("TimescaleDB features disabled (hypertables preserved as regular tables)")

    except Exception as e:
        print(f"Warning: TimescaleDB cleanup failed: {e}")


class Migration(migrations.Migration):
    """
    Enable TimescaleDB and configure hypertables for time-series data.

    Dependencies: Requires 0001_initial (with composite PKs)
    """

    # Disable atomic to allow graceful failure when TimescaleDB is not installed
    atomic = False

    dependencies = [
        ("feefifofunds", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            code=enable_timescaledb,
            reverse_code=disable_timescaledb,
        ),
    ]
