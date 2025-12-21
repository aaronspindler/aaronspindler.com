from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("photos", "0022_alter_photo_image_alter_photo_image_preview_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="photo",
            name="image_type",
            field=models.CharField(
                choices=[
                    ("portrait", "Portrait"),
                    ("group", "Group Photo"),
                    ("landscape", "Landscape/Nature"),
                    ("architecture", "Architecture"),
                    ("macro", "Macro/Close-up"),
                    ("food", "Food"),
                    ("document", "Document/Text"),
                    ("unknown", "Unknown"),
                ],
                db_index=True,
                default="unknown",
                help_text="Automatically detected image type for optimized cropping",
                max_length=20,
            ),
        ),
    ]
