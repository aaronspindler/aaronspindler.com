# Generated migration for tags and series models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_knowledgegraphscreenshot'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Tag name (e.g., 'Python', 'Django', 'Machine Learning')", max_length=50, unique=True)),
                ('slug', models.SlugField(help_text='URL-friendly version of tag name', unique=True)),
                ('description', models.TextField(blank=True, help_text='Optional description of what this tag represents')),
                ('color', models.CharField(default='#3b82f6', help_text="Hex color code for tag display (e.g., '#3b82f6')", max_length=7)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Tag',
                'verbose_name_plural': 'Tags',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='BlogPostSeries',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Series name (e.g., 'Building a Blog Series')", max_length=200)),
                ('slug', models.SlugField(help_text='URL-friendly series identifier', max_length=200, unique=True)),
                ('description', models.TextField(help_text='Description of what this series covers')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Blog Post Series',
                'verbose_name_plural': 'Blog Post Series',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='BlogPostTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('blog_template_name', models.CharField(help_text='Template name of the blog post', max_length=255)),
                ('blog_category', models.CharField(blank=True, help_text='Category of the blog post', max_length=50, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blog_posts', to='blog.tag')),
            ],
            options={
                'verbose_name': 'Blog Post Tag',
                'verbose_name_plural': 'Blog Post Tags',
            },
        ),
        migrations.CreateModel(
            name='BlogPostSeriesMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('blog_template_name', models.CharField(help_text='Template name of the blog post', max_length=255)),
                ('blog_category', models.CharField(blank=True, help_text='Category of the blog post', max_length=50, null=True)),
                ('part_number', models.PositiveIntegerField(help_text='Part number in the series (e.g., 1, 2, 3)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('series', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='blog.blogpostseries')),
            ],
            options={
                'verbose_name': 'Blog Post Series Membership',
                'verbose_name_plural': 'Blog Post Series Memberships',
                'ordering': ['series', 'part_number'],
            },
        ),
        migrations.AddIndex(
            model_name='tag',
            index=models.Index(fields=['slug'], name='blog_tag_slug_8e8f3a_idx'),
        ),
        migrations.AddIndex(
            model_name='tag',
            index=models.Index(fields=['name'], name='blog_tag_name_4d3426_idx'),
        ),
        migrations.AddIndex(
            model_name='blogpostseriesme_series_d3e8f3_idx',
            index=models.Index(fields=['blog_template_name', 'blog_category'], name='blog_blogpo_blog_te_5fc8d7_idx'),
        ),
        migrations.AddIndex(
            model_name='blogpostseriesme_series_d3e8f3_idx',
            index=models.Index(fields=['series', 'part_number'], name='blog_blogpo_series__f51a96_idx'),
        ),
        migrations.AddIndex(
            model_name='blogposttag',
            index=models.Index(fields=['blog_template_name', 'blog_category'], name='blog_blogpo_blog_te_7e9f2a_idx'),
        ),
        migrations.AddIndex(
            model_name='blogposttag',
            index=models.Index(fields=['tag'], name='blog_blogpo_tag_id_9a8c3f_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='blogposttag',
            unique_together={('blog_template_name', 'blog_category', 'tag')},
        ),
        migrations.AlterUniqueTogether(
            name='blogpostseriesMembership',
            unique_together={('series', 'blog_template_name', 'blog_category'), ('series', 'part_number')},
        ),
    ]

