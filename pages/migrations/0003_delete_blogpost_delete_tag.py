# Generated by Django 5.1 on 2024-09-01 15:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0002_tag_blogpost'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BlogPost',
        ),
        migrations.DeleteModel(
            name='Tag',
        ),
    ]
