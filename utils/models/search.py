"""
Search-related models for full-text search functionality.
"""

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models


class SearchableContent(models.Model):
    """
    Model for storing searchable content from blog posts and other sources.
    Uses PostgreSQL full-text search with trigram similarity for typo tolerance.
    """

    CONTENT_TYPE_CHOICES = [
        ("blog_post", "Blog Post"),
        ("project", "Project"),
        ("book", "Book"),
    ]

    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        db_index=True,
        help_text="Type of content (blog_post, project, book)",
    )

    title = models.CharField(max_length=500, help_text="Content title")
    description = models.TextField(blank=True, help_text="Content description/excerpt")
    content = models.TextField(blank=True, help_text="Full content text for search")

    category = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Category (for blog posts: tech, personal, projects, etc.)",
    )

    url = models.CharField(max_length=500, help_text="URL path to the content")

    template_name = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Template name for blog posts",
    )

    # PostgreSQL full-text search vector
    search_vector = SearchVectorField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "category"]),
            models.Index(fields=["template_name"]),
            GinIndex(fields=["search_vector"], name="search_vector_idx"),
        ]
        verbose_name = "Searchable Content"
        verbose_name_plural = "Searchable Content"

    def __str__(self):
        return f"{self.get_content_type_display()}: {self.title}"

    @classmethod
    def update_search_vector(cls, instance_id):
        """
        Update the search vector for a specific instance.
        Called after saving content to rebuild the search index.
        """
        from django.contrib.postgres.search import SearchVector

        cls.objects.filter(pk=instance_id).update(
            search_vector=SearchVector("title", weight="A")
            + SearchVector("description", weight="B")
            + SearchVector("content", weight="C")
        )
