# Generated by Django 5.1 on 2024-09-01 23:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0003_delete_blogpost_delete_tag'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagevisit',
            name='geo_data',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
