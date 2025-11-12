from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("feefifofunds", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Trade",
        ),
    ]
