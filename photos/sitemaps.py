"""
Sitemaps for the photos app with caching support.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.core.cache import cache
from photos.models import PhotoAlbum, Photo


class PhotoAlbumSitemap(Sitemap):
    """Sitemap for photo albums"""
    changefreq = "weekly"
    priority = 0.7
    protocol = "https"

    def items(self):
        """Return all public photo albums with caching"""
        cache_key = 'sitemap_photo_albums_v1'
        albums = cache.get(cache_key)
        
        if albums is None:
            albums = list(PhotoAlbum.objects.filter(is_private=False).order_by('-created_at'))
            # Cache for 12 hours
            cache.set(cache_key, albums, 43200)
        
        return albums

    def location(self, obj):
        """Get the URL for each album"""
        return reverse('photos:album_detail', kwargs={'slug': obj.slug})

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
    """Sitemap for individual photos (if you have individual photo pages)"""
    changefreq = "monthly"
    priority = 0.5
    protocol = "https"
    limit = 1000  # Limit number of URLs per sitemap

    def items(self):
        """Return all photos from public albums with caching"""
        cache_key = 'sitemap_photos_v1'
        photos = cache.get(cache_key)
        
        if photos is None:
            # Only include photos from public albums
            public_albums = PhotoAlbum.objects.filter(is_private=False).values_list('id', flat=True)
            photos = list(Photo.objects.filter(
                albums__in=public_albums
            ).distinct().select_related().prefetch_related('albums').order_by('-created_at'))
            # Cache for 12 hours
            cache.set(cache_key, photos, 43200)
        
        return photos

    def location(self, obj):
        """Get the URL for each photo"""
        # If you have individual photo pages, return their URLs here
        # For now, we'll link to the album with a photo anchor
        album = obj.albums.filter(is_private=False).first()
        if album:
            return f"{reverse('photos:album_detail', kwargs={'slug': album.slug})}#photo-{obj.id}"
        return None

    def lastmod(self, obj):
        """Return the last modification date"""
        return obj.updated_at

    def priority(self, obj):
        """Set priority for photos"""
        # You can adjust this based on photo properties
        if obj.title:
            return 0.6
        return 0.4