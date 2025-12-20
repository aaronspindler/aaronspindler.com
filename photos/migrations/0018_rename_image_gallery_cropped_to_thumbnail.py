from django.db import migrations, models


class Migration(migrations.Migration):
    """Rename image_gallery_cropped to image_thumbnail and update upload path."""

    dependencies = [
        ("photos", "0017_remove_image_optimized"),
    ]

    operations = [
        migrations.RenameField(
            model_name="photo",
            old_name="image_gallery_cropped",
            new_name="image_thumbnail",
        ),
        migrations.AlterField(
            model_name="photo",
            name="image_thumbnail",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="photos/thumbnails/",
                verbose_name="Thumbnail Version (Smart Cropped)",
            ),
        ),
    ]
