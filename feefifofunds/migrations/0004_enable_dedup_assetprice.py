from django.db import connections, migrations


def enable_dedup(apps, schema_editor):
    with connections["questdb"].cursor() as cursor:
        cursor.execute("""
            ALTER TABLE assetprice
            DEDUP ENABLE UPSERT KEYS(time, asset_id, interval_minutes, source);
        """)


def disable_dedup(apps, schema_editor):
    with connections["questdb"].cursor() as cursor:
        cursor.execute("ALTER TABLE assetprice DEDUP DISABLE;")


class Migration(migrations.Migration):
    dependencies = [
        ("feefifofunds", "0003_create_questdb_assetprice_table"),
    ]

    operations = [
        migrations.RunPython(
            code=enable_dedup,
            reverse_code=disable_dedup,
        ),
    ]
