"""
Search utilities for blog posts, projects, photos, and other content.
Uses PostgreSQL full-text search with trigram similarity for typo tolerance.
"""

from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramWordSimilarity
from django.db.models import F, Q, Value
from django.db.models.functions import Greatest

from photos.models import Photo, PhotoAlbum
from utils.models import SearchableContent


def search_blog_posts(query=None, category=None):
    """
    Search blog posts using PostgreSQL full-text search with trigram similarity.

    Args:
        query: Search query string (searches titles and content)
        category: Blog category to filter by

    Returns:
        List of blog post dicts with metadata and relevance scores
    """
    # Start with all blog posts
    queryset = SearchableContent.objects.filter(content_type="blog_post")

    # Filter by category if provided
    if category:
        queryset = queryset.filter(category=category)

    # If no query, return all results sorted by date
    if not query:
        return [
            {
                "template_name": obj.template_name,
                "blog_title": obj.title,
                "category": obj.category,
                "entry_number": obj.template_name.split("_")[0],
            }
            for obj in queryset.order_by("-created_at")
        ]

    # Use PostgreSQL full-text search with trigram similarity
    search_query = SearchQuery(query, config="english")

    # Calculate search rank (FTS score)
    queryset = queryset.annotate(
        rank=SearchRank(F("search_vector"), search_query),
    )

    # Calculate trigram word similarity for typo tolerance
    queryset = queryset.annotate(
        title_similarity=TrigramWordSimilarity(query, "title"),
        description_similarity=TrigramWordSimilarity(query, "description"),
    )

    # Combine scores: rank (70%) + best trigram similarity (30%)
    queryset = queryset.annotate(
        similarity=Greatest("title_similarity", "description_similarity"),
        combined_score=F("rank") * Value(0.7) + F("similarity") * Value(0.3),
    )

    queryset = queryset.filter(Q(rank__gt=0.01) | Q(similarity__gt=0.2))
    queryset = queryset.order_by("-combined_score", "-created_at")

    # Convert to dict format
    results = []
    for obj in queryset:
        results.append(
            {
                "template_name": obj.template_name,
                "blog_title": obj.title,
                "blog_content": obj.content[:500] if obj.content else "",  # Truncate for preview
                "category": obj.category,
                "entry_number": obj.template_name.split("_")[0] if obj.template_name else "0000",
                "relevance_score": float(obj.combined_score)
                if hasattr(obj, "combined_score") and obj.combined_score is not None
                else 0.0,
            }
        )

    return results


def search_projects(query=None):
    """
    Search projects using PostgreSQL full-text search with trigram similarity.

    Args:
        query: Search query string (searches name and description)

    Returns:
        List of project dicts with metadata
    """
    # Start with all projects
    queryset = SearchableContent.objects.filter(content_type="project")

    # If no query, return all results
    if not query:
        return [
            {
                "name": obj.title,
                "description": obj.description,
                "link": obj.url,
            }
            for obj in queryset.order_by("title")
        ]

    # Use PostgreSQL full-text search with trigram similarity
    search_query = SearchQuery(query, config="english")

    # Calculate search rank
    queryset = queryset.annotate(
        rank=SearchRank(F("search_vector"), search_query),
    )

    # Calculate trigram word similarity
    queryset = queryset.annotate(
        title_similarity=TrigramWordSimilarity(query, "title"),
        description_similarity=TrigramWordSimilarity(query, "description"),
    )

    # Combine scores
    queryset = queryset.annotate(
        similarity=Greatest("title_similarity", "description_similarity"),
        combined_score=F("rank") * Value(0.7) + F("similarity") * Value(0.3),
    )

    queryset = queryset.filter(Q(rank__gt=0.01) | Q(similarity__gt=0.2))
    queryset = queryset.order_by("-combined_score", "title")

    # Convert to dict format
    results = []
    for obj in queryset:
        results.append(
            {
                "name": obj.title,
                "description": obj.description,
                "link": obj.url,
            }
        )

    return results


def search_books(query=None):
    """
    Search books using PostgreSQL full-text search with trigram similarity.

    Args:
        query: Search query string (searches name, author, and quote)

    Returns:
        List of book dicts
    """
    # Start with all books
    queryset = SearchableContent.objects.filter(content_type="book")

    # If no query, return all results
    if not query:
        return [
            {
                "name": obj.title,
                "author": obj.description.replace("by ", "") if obj.description.startswith("by ") else obj.description,
                "favourite_quote": obj.content,
            }
            for obj in queryset.order_by("title")
        ]

    # Use PostgreSQL full-text search with trigram similarity
    search_query = SearchQuery(query, config="english")

    # Calculate search rank
    queryset = queryset.annotate(
        rank=SearchRank(F("search_vector"), search_query),
    )

    # Calculate trigram word similarity
    queryset = queryset.annotate(
        title_similarity=TrigramWordSimilarity(query, "title"),
        description_similarity=TrigramWordSimilarity(query, "description"),
        content_similarity=TrigramWordSimilarity(query, "content"),
    )

    # Combine scores
    queryset = queryset.annotate(
        similarity=Greatest("title_similarity", "description_similarity", "content_similarity"),
        combined_score=F("rank") * Value(0.7) + F("similarity") * Value(0.3),
    )

    queryset = queryset.filter(Q(rank__gt=0.01) | Q(similarity__gt=0.2))
    queryset = queryset.order_by("-combined_score", "title")

    # Convert to dict format
    results = []
    for obj in queryset:
        results.append(
            {
                "name": obj.title,
                "author": obj.description.replace("by ", "") if obj.description.startswith("by ") else obj.description,
                "favourite_quote": obj.content,
            }
        )

    return results


def search_photos(query=None):
    """
    Search photos using PostgreSQL full-text search with trigram similarity.

    Args:
        query: Search query string (searches title and description)

    Returns:
        QuerySet of Photo objects ordered by relevance
    """
    queryset = Photo.objects.all()

    if not query:
        return queryset.order_by("-created_at")

    # Use PostgreSQL full-text search
    search_query = SearchQuery(query, config="english")

    # Calculate search rank
    queryset = queryset.annotate(
        rank=SearchRank(F("search_vector"), search_query),
    )

    # Calculate trigram word similarity
    queryset = queryset.annotate(
        title_similarity=TrigramWordSimilarity(query, "title"),
        description_similarity=TrigramWordSimilarity(query, "description"),
    )

    # Combine scores
    queryset = queryset.annotate(
        similarity=Greatest("title_similarity", "description_similarity"),
        combined_score=F("rank") * Value(0.7) + F("similarity") * Value(0.3),
    )

    queryset = queryset.filter(Q(rank__gt=0.01) | Q(similarity__gt=0.2))
    return queryset.order_by("-combined_score", "-created_at")


def search_photo_albums(query=None):
    """
    Search photo albums using PostgreSQL full-text search with trigram similarity.

    Args:
        query: Search query string (searches title and description)

    Returns:
        QuerySet of PhotoAlbum objects ordered by relevance
    """
    queryset = PhotoAlbum.objects.all()

    if not query:
        return queryset.order_by("-created_at")

    # Use PostgreSQL full-text search
    search_query = SearchQuery(query, config="english")

    # Calculate search rank
    queryset = queryset.annotate(
        rank=SearchRank(F("search_vector"), search_query),
    )

    # Calculate trigram word similarity
    queryset = queryset.annotate(
        title_similarity=TrigramWordSimilarity(query, "title"),
        description_similarity=TrigramWordSimilarity(query, "description"),
    )

    # Combine scores
    queryset = queryset.annotate(
        similarity=Greatest("title_similarity", "description_similarity"),
        combined_score=F("rank") * Value(0.7) + F("similarity") * Value(0.3),
    )

    queryset = queryset.filter(Q(rank__gt=0.01) | Q(similarity__gt=0.2))
    return queryset.order_by("-combined_score", "-created_at")
