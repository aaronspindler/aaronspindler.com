from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utils', '0025_add_ban_model_and_referer'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='trackedrequest',
            index=models.Index(fields=['path'], name='utils_track_path_idx'),
        ),
        migrations.AddIndex(
            model_name='trackedrequest',
            index=models.Index(fields=['browser'], name='utils_track_browser_idx'),
        ),
        migrations.AddIndex(
            model_name='trackedrequest',
            index=models.Index(fields=['os'], name='utils_track_os_idx'),
        ),
        migrations.AddIndex(
            model_name='trackedrequest',
            index=models.Index(fields=['fingerprint_obj', '-created_at'], name='utils_track_fp_created_idx'),
        ),
    ]
