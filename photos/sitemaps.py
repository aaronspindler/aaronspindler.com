"""
Sitemaps for the photos app with caching support.
"""

from django.contrib.sitemaps import Sitemap
from django.core.cache import cache
from django.urls import reverse

from photos.models import Photo, PhotoAlbum


class PhotoAlbumSitemap(Sitemap):
    """Sitemap for photo albums"""

    changefreq = "weekly"
    # priority is defined as a method below
    protocol = "https"

    def items(self):
        """Return all public photo albums with caching"""
        cache_key = "sitemap_photo_albums_v1"
        albums = cache.get(cache_key)

        if albums is None:
            albums = list(PhotoAlbum.objects.filter(is_private=False).order_by("-created_at"))
            cache.set(cache_key, albums, 43200)  # Cache for 12 hours

        return albums

    def location(self, obj):
        """Get the URL for each album"""
        return reverse("photos:album_detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj):
        """Return the last modification date"""
        return obj.updated_at

    def priority(self, obj):
        """Adjust priority based on photo count and recency"""
        # Albums with more photos get slightly higher priority
        photo_count = obj.photos.count()
        if photo_count >= 20:
            return 0.8
        elif photo_count >= 10:
            return 0.7
        elif photo_count >= 5:
            return 0.6
        else:
            return 0.5


class PhotoSitemap(Sitemap):
    """Sitemap for individual photo detail pages."""

    changefreq = "monthly"
    # priority is defined as a method below
    protocol = "https"
    limit = 1000  # Limit number of URLs per sitemap

    def items(self):
        """
        Return only photos that belong to at least one public album.

        Photos that are exclusively in private albums are excluded from the sitemap
        to prevent exposing URLs that would return 404 for anonymous users.
        """
        cache_key = "sitemap_photos_v2"
        photos = cache.get(cache_key)

        if photos is None:
            public_album_ids = PhotoAlbum.objects.filter(is_private=False).values_list("id", flat=True)
            photos = list(
                Photo.objects.filter(albums__id__in=public_album_ids)
                .distinct()
                .select_related()
                .prefetch_related("albums")
                .order_by("-created_at")
            )
            cache.set(cache_key, photos, 43200)  # Cache for 12 hours

        return photos

    def location(self, obj):
        """Get the URL for each photo's detail page."""
        return reverse("photos:photo_detail", kwargs={"pk": obj.pk})

    def lastmod(self, obj):
        """Return the last modification date"""
        return obj.updated_at

    def priority(self, obj):
        """Set priority for photos"""
        # You can adjust this based on photo properties
        if obj.title:
            return 0.6
        return 0.4
