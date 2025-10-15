# Generated manually for full-text search feature

from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """
    Enable PostgreSQL extensions required for full-text search.
    - pg_trgm: Trigram similarity for typo-tolerant search
    - unaccent: Remove accents from text for better search matching
    """

    dependencies = [
        ("blog", "0004_make_blog_category_required"),
    ]

    operations = [
        TrigramExtension(),
        UnaccentExtension(),
    ]
