from django.conf import settings
from django.db import connections, migrations


def _is_questdb_available():
    """Check if QuestDB is actually configured (not a PostgreSQL fallback)."""
    if getattr(settings, "TESTING", False):
        return False
    questdb_config = settings.DATABASES.get("questdb", {})
    return questdb_config.get("ENGINE") == "config.db_backends.questdb"


def create_assetprice_table_with_dedup(_apps, _schema_editor):
    if not _is_questdb_available():
        return
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
        cursor.execute("""
            ALTER TABLE assetprice
            DEDUP ENABLE UPSERT KEYS(time, asset_id, interval_minutes, source, quote_currency);
        """)


def drop_assetprice_table(_apps, _schema_editor):
    if not _is_questdb_available():
        return
    with connections["questdb"].cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS assetprice;")


class Migration(migrations.Migration):
    dependencies = [
        ("feefifofunds", "0002_remove_trade_model"),
    ]

    operations = [
        migrations.RunPython(
            code=create_assetprice_table_with_dedup,
            reverse_code=drop_assetprice_table,
        ),
    ]
