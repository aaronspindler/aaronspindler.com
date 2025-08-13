"""
Migration to add performance indexes for the photos app.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('photos', '0001_initial'),
    ]

    operations = [
        # Add indexes for Album model
        migrations.AddIndex(
            model_name='album',
            index=models.Index(fields=['is_published', 'order', '-created_at'], 
                              name='photos_album_published_idx'),
        ),
        migrations.AddIndex(
            model_name='album',
            index=models.Index(fields=['is_published', '-created_at'], 
                              name='photos_album_pub_created_idx'),
        ),
        migrations.AddIndex(
            model_name='album',
            index=models.Index(fields=['order'], 
                              name='photos_album_order_idx'),
        ),
        
        # Add indexes for Photo model
        migrations.AddIndex(
            model_name='photo',
            index=models.Index(fields=['album', 'order', '-created_at'], 
                              name='photos_photo_album_order_idx'),
        ),
        migrations.AddIndex(
            model_name='photo',
            index=models.Index(fields=['album', '-created_at'], 
                              name='photos_photo_album_created_idx'),
        ),
        migrations.AddIndex(
            model_name='photo',
            index=models.Index(fields=['order'], 
                              name='photos_photo_order_idx'),
        ),
        
        # Add composite index for common query patterns
        migrations.AddIndex(
            model_name='photo',
            index=models.Index(fields=['album', 'order'], 
                              name='photos_photo_album_ord_idx'),
        ),
    ]