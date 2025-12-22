from django.contrib.sitemaps import Sitemap
from django.core.cache import cache
from django.urls import reverse

from photos.models import Photo, PhotoAlbum


class PhotoAlbumSitemap(Sitemap):
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        cache_key = "sitemap_photo_albums_v1"
        albums = cache.get(cache_key)

        if albums is None:
            albums = list(PhotoAlbum.objects.filter(is_private=False).order_by("-created_at"))
            cache.set(cache_key, albums, 43200)  # Cache for 12 hours

        return albums

    def location(self, obj):
        return reverse("photos:album_detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj):
        return obj.updated_at

    def priority(self, obj):
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
    changefreq = "monthly"
    protocol = "https"
    limit = 1000  # Limit number of URLs per sitemap

    def items(self):
        cache_key = "sitemap_photos_v1"
        photos = cache.get(cache_key)

        if photos is None:
            public_albums = PhotoAlbum.objects.filter(is_private=False).values_list("id", flat=True)
            photos = list(
                Photo.objects.filter(albums__in=public_albums)
                .distinct()
                .select_related()
                .prefetch_related("albums")
                .order_by("-created_at")
            )
            cache.set(cache_key, photos, 43200)  # Cache for 12 hours

        return photos

    def location(self, obj):
        album = obj.albums.filter(is_private=False).first()
        if album:
            return f"{reverse('photos:album_detail', kwargs={'slug': album.slug})}#photo-{obj.id}"
        return None

    def lastmod(self, obj):
        return obj.updated_at

    def priority(self, obj):
        if obj.title:
            return 0.6
        return 0.4
