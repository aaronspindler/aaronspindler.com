import uuid

from django.db import migrations, models


def generate_uuids(apps, _schema_editor):
    """Generate UUIDs for existing photos."""
    Photo = apps.get_model("photos", "Photo")
    for photo in Photo.objects.all():
        photo.uuid = uuid.uuid4()
        photo.save(update_fields=["uuid"])


class Migration(migrations.Migration):
    dependencies = [
        ("photos", "0020_remove_photo_title_description"),
    ]

    operations = [
        # Step 1: Add UUID field with null allowed
        migrations.AddField(
            model_name="photo",
            name="uuid",
            field=models.UUIDField(null=True, blank=True),
        ),
        # Step 2: Populate UUIDs for existing records
        migrations.RunPython(generate_uuids, reverse_code=migrations.RunPython.noop),
        # Step 3: Make field required and add constraints
        migrations.AlterField(
            model_name="photo",
            name="uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                db_index=True,
            ),
        ),
    ]
