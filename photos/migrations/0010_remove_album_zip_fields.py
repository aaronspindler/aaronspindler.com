from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("photos", "0009_add_search_fields_and_indexes"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="photoalbum",
            name="zip_file",
        ),
        migrations.RemoveField(
            model_name="photoalbum",
            name="zip_file_optimized",
        ),
    ]
