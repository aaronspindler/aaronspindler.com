from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramWordSimilarity
from django.db.models import F, Q, Value
from django.db.models.functions import Greatest

from photos.models import Photo, PhotoAlbum
from utils.models import SearchableContent


def search_blog_posts(query=None, category=None):
    queryset = SearchableContent.objects.filter(content_type="blog_post")

    if category:
        queryset = queryset.filter(category=category)

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
    queryset = SearchableContent.objects.filter(content_type="project")

    if not query:
        return [
            {
                "name": obj.title,
                "description": obj.description,
                "link": obj.url,
            }
            for obj in queryset.order_by("title")
        ]

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
    queryset = SearchableContent.objects.filter(content_type="book")

    if not query:
        return [
            {
                "name": obj.title,
                "author": obj.description.replace("by ", "") if obj.description.startswith("by ") else obj.description,
                "favourite_quote": obj.content,
            }
            for obj in queryset.order_by("title")
        ]

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
    queryset = Photo.objects.all()

    if not query:
        return queryset.order_by("-created_at")

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

    queryset = queryset.annotate(
        similarity=Greatest("title_similarity", "description_similarity"),
        combined_score=F("rank") * Value(0.7) + F("similarity") * Value(0.3),
    )

    queryset = queryset.filter(Q(rank__gt=0.01) | Q(similarity__gt=0.2))
    return queryset.order_by("-combined_score", "-created_at")


def search_photo_albums(query=None):
    queryset = PhotoAlbum.objects.all()

    if not query:
        return queryset.order_by("-created_at")

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

    queryset = queryset.annotate(
        similarity=Greatest("title_similarity", "description_similarity"),
        combined_score=F("rank") * Value(0.7) + F("similarity") * Value(0.3),
    )

    queryset = queryset.filter(Q(rank__gt=0.01) | Q(similarity__gt=0.2))
    return queryset.order_by("-combined_score", "-created_at")
