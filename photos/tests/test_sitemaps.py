"""
Tests for photo sitemaps.

Tests verify that only photos in public albums are included in the sitemap,
and photos exclusively in private albums are excluded.
"""

import gc
from io import BytesIO

from django.core.cache import cache
from django.test import TestCase
from PIL import Image

from photos.models import Photo, PhotoAlbum
from photos.sitemaps import PhotoAlbumSitemap, PhotoSitemap
from photos.tests.factories import PhotoFactory


class PhotoSitemapTestCase(TestCase):
    """Test cases for PhotoSitemap."""

    def setUp(self):
        """Set up test data."""
        cache.clear()

        self.public_album = PhotoFactory.create_photo_album(
            title="Public Album",
            slug="public-album-sitemap",
            is_private=False,
        )

        self.private_album = PhotoFactory.create_photo_album(
            title="Private Album",
            slug="private-album-sitemap",
            is_private=True,
        )

        # Photo only in public album
        self.public_only_photo = self._create_test_photo("Public Only Photo")
        self.public_album.photos.add(self.public_only_photo)

        # Photo only in private album
        self.private_only_photo = self._create_test_photo("Private Only Photo")
        self.private_album.photos.add(self.private_only_photo)

        # Photo in both public and private albums
        self.both_albums_photo = self._create_test_photo("Both Albums Photo")
        self.public_album.photos.add(self.both_albums_photo)
        self.private_album.photos.add(self.both_albums_photo)

    def _create_test_photo(self, title):
        """Helper to create a test photo with unique image."""
        img = Image.new(
            "RGB",
            (10, 10),
            color=(hash(title) % 256, (hash(title) * 2) % 256, (hash(title) * 3) % 256),
        )
        img_io = BytesIO()
        img.save(img_io, format="JPEG", quality=50)
        img_io.seek(0)

        from django.core.files.uploadedfile import SimpleUploadedFile

        test_image = SimpleUploadedFile(
            name=f"{title.lower().replace(' ', '_')}.jpg",
            content=img_io.getvalue(),
            content_type="image/jpeg",
        )

        photo = Photo(title=title, image=test_image)
        photo.save(skip_duplicate_check=True)
        return photo

    def tearDown(self):
        """Clean up resources after each test."""
        cache.clear()
        Photo.objects.all().delete()
        PhotoAlbum.objects.all().delete()
        gc.collect()

    def test_sitemap_includes_public_album_photos(self):
        """Test photos in public albums are included in sitemap."""
        sitemap = PhotoSitemap()
        items = sitemap.items()
        photo_ids = [p.pk for p in items]

        self.assertIn(self.public_only_photo.pk, photo_ids)

    def test_sitemap_excludes_private_only_photos(self):
        """Test photos exclusively in private albums are excluded from sitemap."""
        sitemap = PhotoSitemap()
        items = sitemap.items()
        photo_ids = [p.pk for p in items]

        self.assertNotIn(self.private_only_photo.pk, photo_ids)

    def test_sitemap_includes_photos_in_both_album_types(self):
        """Test photos in both public and private albums are included."""
        sitemap = PhotoSitemap()
        items = sitemap.items()
        photo_ids = [p.pk for p in items]

        self.assertIn(self.both_albums_photo.pk, photo_ids)

    def test_sitemap_location_returns_photo_detail_url(self):
        """Test sitemap returns correct photo detail URL."""
        sitemap = PhotoSitemap()
        url = sitemap.location(self.public_only_photo)

        self.assertEqual(url, f"/photos/photo/{self.public_only_photo.pk}/")

    def test_sitemap_no_duplicate_entries(self):
        """Test photos in multiple public albums appear only once."""
        # Add another public album with the same photo
        another_public = PhotoFactory.create_photo_album(
            title="Another Public",
            slug="another-public-sitemap",
            is_private=False,
        )
        another_public.photos.add(self.public_only_photo)

        cache.clear()
        sitemap = PhotoSitemap()
        items = sitemap.items()
        photo_ids = [p.pk for p in items]

        # Count occurrences of public_only_photo
        count = photo_ids.count(self.public_only_photo.pk)
        self.assertEqual(count, 1)


class PhotoAlbumSitemapTestCase(TestCase):
    """Test cases for PhotoAlbumSitemap."""

    def setUp(self):
        """Set up test data."""
        cache.clear()

        self.public_album = PhotoFactory.create_photo_album(
            title="Public Album",
            slug="public-album-sitemap-test",
            is_private=False,
        )

        self.private_album = PhotoFactory.create_photo_album(
            title="Private Album",
            slug="private-album-sitemap-test",
            is_private=True,
        )

    def tearDown(self):
        """Clean up resources after each test."""
        cache.clear()
        PhotoAlbum.objects.all().delete()
        gc.collect()

    def test_sitemap_includes_public_albums(self):
        """Test public albums are included in sitemap."""
        sitemap = PhotoAlbumSitemap()
        items = sitemap.items()
        album_ids = [a.pk for a in items]

        self.assertIn(self.public_album.pk, album_ids)

    def test_sitemap_excludes_private_albums(self):
        """Test private albums are excluded from sitemap."""
        sitemap = PhotoAlbumSitemap()
        items = sitemap.items()
        album_ids = [a.pk for a in items]

        self.assertNotIn(self.private_album.pk, album_ids)
