from django.db import migrations, models
import django.db.models.deletion


def migrate_existing_album_photos(apps, schema_editor):
    """Migrate existing M2M relationships to the through table."""
    AlbumPhoto = apps.get_model("photos", "AlbumPhoto")

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT photoalbum_id, photo_id FROM photos_photoalbum_photos"
        )
        rows = cursor.fetchall()

    for album_id, photo_id in rows:
        AlbumPhoto.objects.get_or_create(
            album_id=album_id,
            photo_id=photo_id,
            defaults={"is_featured": False, "display_order": 0},
        )


def reverse_migrate_album_photos(apps, schema_editor):
    """Reverse migration - copy data back to original M2M table."""
    AlbumPhoto = apps.get_model("photos", "AlbumPhoto")

    with schema_editor.connection.cursor() as cursor:
        for ap in AlbumPhoto.objects.all():
            cursor.execute(
                "INSERT INTO photos_photoalbum_photos (photoalbum_id, photo_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                [ap.album_id, ap.photo_id],
            )


class Migration(migrations.Migration):
    dependencies = [
        ("photos", "0011_add_album_sharing"),
    ]

    operations = [
        # Add ZIP fields to PhotoAlbum
        migrations.AddField(
            model_name="photoalbum",
            name="zip_file",
            field=models.FileField(
                blank=True,
                help_text="ZIP file containing optimized photos from this album",
                null=True,
                upload_to="albums/zips/",
            ),
        ),
        migrations.AddField(
            model_name="photoalbum",
            name="zip_content_hash",
            field=models.CharField(
                blank=True,
                help_text="SHA-256 hash of photo IDs + file hashes for change detection",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="photoalbum",
            name="zip_generated_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When the ZIP file was last generated",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="photoalbum",
            name="zip_generation_status",
            field=models.CharField(
                choices=[
                    ("none", "Not Generated"),
                    ("pending", "Generation Pending"),
                    ("generating", "Generating"),
                    ("ready", "Ready"),
                    ("failed", "Generation Failed"),
                ],
                default="none",
                help_text="Current status of ZIP file generation",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="photoalbum",
            name="zip_file_size",
            field=models.PositiveBigIntegerField(
                blank=True,
                help_text="Size of ZIP file in bytes",
                null=True,
            ),
        ),
        # Create AlbumPhoto through table
        migrations.CreateModel(
            name="AlbumPhoto",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "is_featured",
                    models.BooleanField(
                        default=False,
                        help_text="Display this photo at 2x2 size in the grid",
                    ),
                ),
                (
                    "display_order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Order within the album (0 = use date_taken order)",
                    ),
                ),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                (
                    "album",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="album_photos",
                        to="photos.photoalbum",
                    ),
                ),
                (
                    "photo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="album_memberships",
                        to="photos.photo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Album Photo",
                "verbose_name_plural": "Album Photos",
                "ordering": ["display_order", "-photo__date_taken", "-added_at"],
                "unique_together": {("album", "photo")},
            },
        ),
        # Migrate existing M2M data to through table
        migrations.RunPython(
            migrate_existing_album_photos,
            reverse_migrate_album_photos,
        ),
        # Remove the old M2M field
        migrations.RemoveField(
            model_name="photoalbum",
            name="photos",
        ),
        # Add the new M2M field with through table
        migrations.AddField(
            model_name="photoalbum",
            name="photos",
            field=models.ManyToManyField(
                through="photos.AlbumPhoto",
                related_name="albums",
                to="photos.photo",
            ),
        ),
    ]
