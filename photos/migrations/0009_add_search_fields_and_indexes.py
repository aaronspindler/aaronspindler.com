# Generated manually for full-text search feature

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import migrations


def populate_photo_search_vectors(apps, schema_editor):  # noqa: ARG001
    """Populate search vectors for existing Photo records."""
    Photo = apps.get_model("photos", "Photo")
    for photo in Photo.objects.all():
        Photo.objects.filter(pk=photo.pk).update(
            search_vector=SearchVector("title", weight="A") + SearchVector("description", weight="B")
        )


def populate_album_search_vectors(apps, schema_editor):  # noqa: ARG001
    """Populate search vectors for existing PhotoAlbum records."""
    PhotoAlbum = apps.get_model("photos", "PhotoAlbum")
    for album in PhotoAlbum.objects.all():
        PhotoAlbum.objects.filter(pk=album.pk).update(
            search_vector=SearchVector("title", weight="A") + SearchVector("description", weight="B")
        )


class Migration(migrations.Migration):
    """
    Add full-text search capabilities to Photo and PhotoAlbum models.
    - Add SearchVectorField to both models
    - Create GIN indexes for fast full-text search
    - Create trigram indexes for typo-tolerant search
    """

    dependencies = [
        ("photos", "0008_photoalbum_zip_file_photoalbum_zip_file_optimized"),
    ]

    operations = [
        # Add search_vector field to Photo
        migrations.AddField(
            model_name="photo",
            name="search_vector",
            field=SearchVectorField(blank=True, null=True),
        ),
        # Add search_vector field to PhotoAlbum
        migrations.AddField(
            model_name="photoalbum",
            name="search_vector",
            field=SearchVectorField(blank=True, null=True),
        ),
        # Populate search vectors for existing records
        migrations.RunPython(populate_photo_search_vectors, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(populate_album_search_vectors, reverse_code=migrations.RunPython.noop),
        # Add GIN index for Photo search_vector
        migrations.AddIndex(
            model_name="photo",
            index=GinIndex(fields=["search_vector"], name="photo_search_idx"),
        ),
        # Add GIN index for PhotoAlbum search_vector
        migrations.AddIndex(
            model_name="photoalbum",
            index=GinIndex(fields=["search_vector"], name="album_search_idx"),
        ),
    ]
