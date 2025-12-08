# Generated manually for adding album sharing with unique tokens

import uuid
from django.db import migrations, models


def generate_unique_tokens(apps, schema_editor):
    """Generate unique tokens for existing albums."""
    PhotoAlbum = apps.get_model('photos', 'PhotoAlbum')
    for album in PhotoAlbum.objects.all():
        album.share_token = uuid.uuid4()
        album.save(update_fields=['share_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('photos', '0010_remove_album_zip_fields'),
    ]

    operations = [
        # Step 1: Add share_token without unique constraint
        migrations.AddField(
            model_name='photoalbum',
            name='share_token',
            field=models.UUIDField(default=uuid.uuid4, db_index=True),
        ),
        # Step 2: Add analytics fields
        migrations.AddField(
            model_name='photoalbum',
            name='share_access_count',
            field=models.PositiveIntegerField(default=0, help_text='Number of times the share link has been accessed'),
        ),
        migrations.AddField(
            model_name='photoalbum',
            name='share_last_accessed',
            field=models.DateTimeField(blank=True, help_text='Last time the share link was accessed', null=True),
        ),
        # Step 3: Generate unique tokens for existing albums
        migrations.RunPython(generate_unique_tokens, reverse_code=migrations.RunPython.noop),
        # Step 4: Add unique constraint to share_token
        migrations.AlterField(
            model_name='photoalbum',
            name='share_token',
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                db_index=True,
                help_text='Unique token for sharing this private album externally'
            ),
        ),
    ]
