from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("feefifofunds", "0001_initial"),
    ]

    operations = [
        # Configure AssetPrice compression
        migrations.RunSQL(
            sql="""
                ALTER TABLE feefifofunds_assetprice SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'asset_id,interval_minutes,source',
                    timescaledb.compress_orderby = 'time DESC'
                );
            """,
            reverse_sql="""
                ALTER TABLE feefifofunds_assetprice SET (
                    timescaledb.compress = false
                );
            """,
        ),
        migrations.RunSQL(
            sql="""
                SELECT add_compression_policy('feefifofunds_assetprice', INTERVAL '7 days');
            """,
            reverse_sql="""
                SELECT remove_compression_policy('feefifofunds_assetprice');
            """,
        ),
        # Configure Trade compression
        migrations.RunSQL(
            sql="""
                ALTER TABLE feefifofunds_trade SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'asset_id,source',
                    timescaledb.compress_orderby = 'time DESC'
                );
            """,
            reverse_sql="""
                ALTER TABLE feefifofunds_trade SET (
                    timescaledb.compress = false
                );
            """,
        ),
        migrations.RunSQL(
            sql="""
                SELECT add_compression_policy('feefifofunds_trade', INTERVAL '1 day');
            """,
            reverse_sql="""
                SELECT remove_compression_policy('feefifofunds_trade');
            """,
        ),
    ]
