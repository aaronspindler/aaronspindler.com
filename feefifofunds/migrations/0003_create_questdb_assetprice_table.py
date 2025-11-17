from django.db import connections, migrations


def create_assetprice_table(apps, schema_editor):
    with connections["questdb"].cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assetprice (
                asset_id INT,
                time TIMESTAMP,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                interval_minutes INT,
                trade_count INT,
                quote_currency SYMBOL CAPACITY 256 CACHE,
                source SYMBOL CAPACITY 256 CACHE
            ) timestamp(time) PARTITION BY DAY;
        """)


def drop_assetprice_table(apps, schema_editor):
    with connections["questdb"].cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS assetprice;")


class Migration(migrations.Migration):
    dependencies = [
        ("feefifofunds", "0002_remove_trade_model"),
    ]

    operations = [
        migrations.RunPython(
            code=create_assetprice_table,
            reverse_code=drop_assetprice_table,
        ),
    ]
