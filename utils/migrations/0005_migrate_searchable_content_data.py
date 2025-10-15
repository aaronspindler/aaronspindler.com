# Generated manually to migrate SearchableContent data from blog to utils

from django.db import migrations


def migrate_searchable_content_data(apps, schema_editor):
    """
    Migrate data from blog_searchablecontent to utils_searchablecontent.
    This is needed because we're moving the SearchableContent model from blog to utils.

    If the blog_searchablecontent table doesn't exist (already deleted), skip the migration.
    """
    _db_alias = schema_editor.connection.alias

    # Check if the blog_searchablecontent table exists
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'blog_searchablecontent'
            );
            """
        )
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            # Table already deleted, nothing to migrate
            return

        # Copy data from blog table to utils table
        cursor.execute(
            """
            INSERT INTO utils_searchablecontent (
                id, content_type, title, description, content, category,
                url, template_name, search_vector, created_at, updated_at
            )
            SELECT
                id, content_type, title, description, content, category,
                url, template_name, search_vector, created_at, updated_at
            FROM blog_searchablecontent
            ON CONFLICT (id) DO NOTHING;
            """
        )


def reverse_migration(apps, schema_editor):
    """
    Reverse the migration by copying data back to blog_searchablecontent.
    """
    _db_alias = schema_editor.connection.alias

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO blog_searchablecontent (
                id, content_type, title, description, content, category,
                url, template_name, search_vector, created_at, updated_at
            )
            SELECT
                id, content_type, title, description, content, category,
                url, template_name, search_vector, created_at, updated_at
            FROM utils_searchablecontent
            ON CONFLICT (id) DO NOTHING;
            """
        )


class Migration(migrations.Migration):
    """
    Migrate SearchableContent data from blog app to utils app.
    This migration copies all data from blog_searchablecontent to utils_searchablecontent.
    """

    dependencies = [
        ("utils", "0004_searchablecontent"),
        ("blog", "0006_searchablecontent"),  # Ensure the blog table still exists
    ]

    operations = [
        migrations.RunPython(migrate_searchable_content_data, reverse_code=reverse_migration),
    ]
