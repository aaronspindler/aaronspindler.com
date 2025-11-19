"""
Tests for Photos sitemaps.

These tests verify the sitemap functionality for PhotoAlbum and Photo models,
including caching behavior, URL generation, and priority calculations.
"""

from datetime import datetime
from datetime import timezone as dt_timezone
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from photos.sitemaps import PhotoAlbumSitemap, PhotoSitemap
from photos.tests.factories import PhotoFactory


class PhotoAlbumSitemapTest(TestCase):
    """Test cases for the PhotoAlbum sitemap."""

    def setUp(self):
        """Set up test data."""
        self.sitemap = PhotoAlbumSitemap()
        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    def test_sitemap_basic_properties(self):
        """Test basic sitemap properties."""
        actual_changefreq = self.sitemap.changefreq
        expected_changefreq = "weekly"
        message = f"Changefreq is '{actual_changefreq}', expected '{expected_changefreq}'"
        self.assertEqual(actual_changefreq, expected_changefreq, message)

        actual_priority = self.sitemap.priority
        expected_priority = 0.7
        message = f"Default priority is {actual_priority}, expected {expected_priority}"
        self.assertEqual(actual_priority, expected_priority, message)

        actual_protocol = self.sitemap.protocol
        expected_protocol = "https"
        message = f"Protocol is '{actual_protocol}', expected '{expected_protocol}'"
        self.assertEqual(actual_protocol, expected_protocol, message)

    def test_items_returns_only_public_albums(self):
        """Test that items() returns only public albums."""
        # Create public and private albums
        PhotoFactory.create_photo_album(title="Public 1", is_private=False)
        PhotoFactory.create_photo_album(title="Public 2", is_private=False)
        PhotoFactory.create_photo_album(title="Private", is_private=True)

        items = self.sitemap.items()

        actual_count = len(items)
        expected_count = 2
        message = f"Sitemap has {actual_count} items, expected {expected_count} (only public)"
        self.assertEqual(actual_count, expected_count, message)

        # Check that only public albums are included
        album_titles = [album.title for album in items]
        actual_has_public1 = "Public 1" in album_titles
        expected_has_public1 = True
        message = f"Sitemap contains 'Public 1': {actual_has_public1}, expected {expected_has_public1}"
        self.assertEqual(actual_has_public1, expected_has_public1, message)

        actual_has_private = "Private" in album_titles
        expected_has_private = False
        message = f"Sitemap contains 'Private': {actual_has_private}, expected {expected_has_private}"
        self.assertEqual(actual_has_private, expected_has_private, message)

    def test_items_caching(self):
        """Test that items are cached."""
        # Create an album
        PhotoFactory.create_photo_album(title="Cached Album", is_private=False)

        # First call should set cache
        items1 = self.sitemap.items()

        actual_count = len(items1)
        expected_count = 1
        message = f"First call returns {actual_count} items, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

        # Check cache was set
        cache_key = "sitemap_photo_albums_v1"
        cached_items = cache.get(cache_key)

        actual_cached = cached_items is not None
        expected_cached = True
        message = f"Items are cached: {actual_cached}, expected {expected_cached}"
        self.assertEqual(actual_cached, expected_cached, message)

        # Create another album
        PhotoFactory.create_photo_album(title="New Album", is_private=False)

        # Second call should return cached items (not include new album)
        items2 = self.sitemap.items()

        actual_count = len(items2)
        expected_count = 1  # Should still be 1 due to cache
        message = f"Cached call returns {actual_count} items, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

        # Clear cache and try again
        cache.clear()
        items3 = self.sitemap.items()

        actual_count = len(items3)
        expected_count = 2  # Now should see both albums
        message = f"After cache clear returns {actual_count} items, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

    def test_location(self):
        """Test location method returns correct URL."""
        album = PhotoFactory.create_photo_album(slug="test-album")

        actual_location = self.sitemap.location(album)
        expected_location = reverse("photos:album_detail", kwargs={"slug": "test-album"})
        message = f"Location is '{actual_location}', expected '{expected_location}'"
        self.assertEqual(actual_location, expected_location, message)

    def test_lastmod(self):
        """Test lastmod returns updated_at timestamp."""
        test_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=dt_timezone.utc)
        album = PhotoFactory.create_photo_album()
        album.updated_at = test_time

        actual_lastmod = self.sitemap.lastmod(album)
        expected_lastmod = test_time
        message = f"Lastmod is {actual_lastmod}, expected {expected_lastmod}"
        self.assertEqual(actual_lastmod, expected_lastmod, message)

    def test_priority_based_on_photo_count(self):
        """Test that priority varies based on photo count."""
        album = PhotoFactory.create_photo_album()

        # Test with 0 photos
        with patch.object(album.photos, "count", return_value=0):
            actual_priority = self.sitemap.priority(album)
            expected_priority = 0.5
            message = f"Priority with 0 photos is {actual_priority}, expected {expected_priority}"
            self.assertEqual(actual_priority, expected_priority, message)

        # Test with 5 photos
        with patch.object(album.photos, "count", return_value=5):
            actual_priority = self.sitemap.priority(album)
            expected_priority = 0.6
            message = f"Priority with 5 photos is {actual_priority}, expected {expected_priority}"
            self.assertEqual(actual_priority, expected_priority, message)

        # Test with 10 photos
        with patch.object(album.photos, "count", return_value=10):
            actual_priority = self.sitemap.priority(album)
            expected_priority = 0.7
            message = f"Priority with 10 photos is {actual_priority}, expected {expected_priority}"
            self.assertEqual(actual_priority, expected_priority, message)

        # Test with 20 photos
        with patch.object(album.photos, "count", return_value=20):
            actual_priority = self.sitemap.priority(album)
            expected_priority = 0.8
            message = f"Priority with 20 photos is {actual_priority}, expected {expected_priority}"
            self.assertEqual(actual_priority, expected_priority, message)

    def test_ordering_by_created_at(self):
        """Test that albums are ordered by created_at descending."""
        # Create albums in specific order
        old = PhotoFactory.create_photo_album(title="Old", is_private=False)
        old.created_at = datetime(2023, 1, 1, tzinfo=dt_timezone.utc)
        old.save()

        new = PhotoFactory.create_photo_album(title="New", is_private=False)
        new.created_at = datetime(2024, 1, 1, tzinfo=dt_timezone.utc)
        new.save()

        items = self.sitemap.items()

        # First item should be the newer one
        actual_first_title = items[0].title
        expected_first_title = "New"
        message = f"First item title is '{actual_first_title}', expected '{expected_first_title}'"
        self.assertEqual(actual_first_title, expected_first_title, message)


class PhotoSitemapTest(TestCase):
    """Test cases for the Photo sitemap."""

    def setUp(self):
        """Set up test data."""
        self.sitemap = PhotoSitemap()
        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    def test_sitemap_basic_properties(self):
        """Test basic sitemap properties."""
        actual_changefreq = self.sitemap.changefreq
        expected_changefreq = "monthly"
        message = f"Changefreq is '{actual_changefreq}', expected '{expected_changefreq}'"
        self.assertEqual(actual_changefreq, expected_changefreq, message)

        actual_priority = self.sitemap.priority
        expected_priority = 0.5
        message = f"Default priority is {actual_priority}, expected {expected_priority}"
        self.assertEqual(actual_priority, expected_priority, message)

        actual_limit = self.sitemap.limit
        expected_limit = 1000
        message = f"Limit is {actual_limit}, expected {expected_limit}"
        self.assertEqual(actual_limit, expected_limit, message)

    def test_items_returns_only_photos_from_public_albums(self):
        """Test that items() returns only photos from public albums."""
        # Create albums
        public_album = PhotoFactory.create_photo_album(title="Public", is_private=False)
        private_album = PhotoFactory.create_photo_album(title="Private", is_private=True)

        # Create photos
        public_photo1 = PhotoFactory.create_photo(title="Public Photo 1")
        public_photo2 = PhotoFactory.create_photo(title="Public Photo 2")
        private_photo = PhotoFactory.create_photo(title="Private Photo")

        # Add photos to albums
        public_album.photos.add(public_photo1, public_photo2)
        private_album.photos.add(private_photo)

        items = self.sitemap.items()

        actual_count = len(items)
        expected_count = 2
        message = f"Sitemap has {actual_count} photos, expected {expected_count} (only from public albums)"
        self.assertEqual(actual_count, expected_count, message)

        photo_titles = [photo.title for photo in items]
        actual_has_private = "Private Photo" in photo_titles
        expected_has_private = False
        message = f"Sitemap contains private photo: {actual_has_private}, expected {expected_has_private}"
        self.assertEqual(actual_has_private, expected_has_private, message)

    def test_items_caching(self):
        """Test that items are cached."""
        # Create album and photo
        album = PhotoFactory.create_photo_album(is_private=False)
        photo = PhotoFactory.create_photo(title="Cached Photo")
        album.photos.add(photo)

        # First call should set cache
        items1 = self.sitemap.items()

        actual_count = len(items1)
        expected_count = 1
        message = f"First call returns {actual_count} items, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

        # Check cache was set
        cache_key = "sitemap_photos_v1"
        cached_items = cache.get(cache_key)

        actual_cached = cached_items is not None
        expected_cached = True
        message = f"Items are cached: {actual_cached}, expected {expected_cached}"
        self.assertEqual(actual_cached, expected_cached, message)

        # Create another photo
        new_photo = PhotoFactory.create_photo(title="New Photo")
        album.photos.add(new_photo)

        # Second call should return cached items
        items2 = self.sitemap.items()

        actual_count = len(items2)
        expected_count = 1  # Should still be 1 due to cache
        message = f"Cached call returns {actual_count} items, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)

    def test_location_with_public_album(self):
        """Test location method returns correct URL with album anchor."""
        album = PhotoFactory.create_photo_album(slug="test-album", is_private=False)
        photo = PhotoFactory.create_photo()
        album.photos.add(photo)

        actual_location = self.sitemap.location(photo)
        expected_location = f"{reverse('photos:album_detail', kwargs={'slug': 'test-album'})}#photo-{photo.id}"
        message = f"Location is '{actual_location}', expected '{expected_location}'"
        self.assertEqual(actual_location, expected_location, message)

    def test_location_with_no_public_album(self):
        """Test location returns None when photo has no public album."""
        # Create photo in private album only
        private_album = PhotoFactory.create_photo_album(is_private=True)
        photo = PhotoFactory.create_photo()
        private_album.photos.add(photo)

        actual_location = self.sitemap.location(photo)
        expected_location = None
        message = f"Location for photo in private album is {actual_location}, expected {expected_location}"
        self.assertEqual(actual_location, expected_location, message)

    def test_location_with_multiple_albums(self):
        """Test location uses first public album when photo is in multiple albums."""
        album1 = PhotoFactory.create_photo_album(slug="album-1", is_private=False)
        album2 = PhotoFactory.create_photo_album(slug="album-2", is_private=False)
        photo = PhotoFactory.create_photo()
        album1.photos.add(photo)
        album2.photos.add(photo)

        location = self.sitemap.location(photo)

        # Should contain one of the album slugs
        actual_has_album_slug = "album-1" in location or "album-2" in location
        expected_has_album_slug = True
        message = f"Location contains album slug: {actual_has_album_slug}, expected {expected_has_album_slug}"
        self.assertEqual(actual_has_album_slug, expected_has_album_slug, message)

        # Should have photo anchor
        actual_has_anchor = f"#photo-{photo.id}" in location
        expected_has_anchor = True
        message = f"Location has photo anchor: {actual_has_anchor}, expected {expected_has_anchor}"
        self.assertEqual(actual_has_anchor, expected_has_anchor, message)

    def test_lastmod(self):
        """Test lastmod returns updated_at timestamp."""
        test_time = datetime(2024, 2, 20, 14, 30, 0, tzinfo=dt_timezone.utc)
        photo = PhotoFactory.create_photo()
        photo.updated_at = test_time

        actual_lastmod = self.sitemap.lastmod(photo)
        expected_lastmod = test_time
        message = f"Lastmod is {actual_lastmod}, expected {expected_lastmod}"
        self.assertEqual(actual_lastmod, expected_lastmod, message)

    def test_priority_based_on_title(self):
        """Test that priority varies based on whether photo has title."""
        # Photo with title
        photo_with_title = PhotoFactory.create_photo(title="Named Photo")
        actual_priority = self.sitemap.priority(photo_with_title)
        expected_priority = 0.6
        message = f"Priority with title is {actual_priority}, expected {expected_priority}"
        self.assertEqual(actual_priority, expected_priority, message)

        # Photo without title
        photo_without_title = PhotoFactory.create_photo(title="")
        actual_priority = self.sitemap.priority(photo_without_title)
        expected_priority = 0.4
        message = f"Priority without title is {actual_priority}, expected {expected_priority}"
        self.assertEqual(actual_priority, expected_priority, message)

    def test_distinct_photos_across_albums(self):
        """Test that photos appearing in multiple albums are only listed once."""
        # Create two public albums
        album1 = PhotoFactory.create_photo_album(is_private=False)
        album2 = PhotoFactory.create_photo_album(is_private=False)

        # Create a photo and add to both albums
        photo = PhotoFactory.create_photo(title="Shared Photo")
        album1.photos.add(photo)
        album2.photos.add(photo)

        items = self.sitemap.items()

        # Count how many times the photo appears
        photo_count = sum(1 for p in items if p.id == photo.id)

        actual_count = photo_count
        expected_count = 1
        message = f"Photo appears {actual_count} times, expected {expected_count} (distinct)"
        self.assertEqual(actual_count, expected_count, message)

    def test_ordering_by_created_at(self):
        """Test that photos are ordered by created_at descending."""
        album = PhotoFactory.create_photo_album(is_private=False)

        # Create photos in specific order
        old_photo = PhotoFactory.create_photo(title="Old")
        old_photo.created_at = datetime(2023, 6, 1, tzinfo=dt_timezone.utc)
        old_photo.save()

        new_photo = PhotoFactory.create_photo(title="New")
        new_photo.created_at = datetime(2024, 6, 1, tzinfo=dt_timezone.utc)
        new_photo.save()

        album.photos.add(old_photo, new_photo)

        items = self.sitemap.items()

        # First item should be the newer one
        actual_first_title = items[0].title
        expected_first_title = "New"
        message = f"First item title is '{actual_first_title}', expected '{expected_first_title}'"
        self.assertEqual(actual_first_title, expected_first_title, message)


class SitemapCacheTest(TestCase):
    """Test cases for sitemap caching behavior."""

    def setUp(self):
        """Set up test data."""
        cache.clear()

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()

    def test_cache_ttl(self):
        """Test that cache TTL is set correctly."""
        album_sitemap = PhotoAlbumSitemap()
        PhotoFactory.create_photo_album(is_private=False)

        # Trigger cache set
        album_sitemap.items()

        # Check cache was set with correct key
        cache_key = "sitemap_photo_albums_v1"
        cached_value = cache.get(cache_key)

        actual_cached = cached_value is not None
        expected_cached = True
        message = f"Value is cached: {actual_cached}, expected {expected_cached}"
        self.assertEqual(actual_cached, expected_cached, message)

        # Note: Testing exact TTL is difficult without mocking time
        # The cache.set call uses 43200 seconds (12 hours)

    @patch("photos.sitemaps.cache")
    def test_cache_miss_triggers_database_query(self, mock_cache):
        """Test that cache miss triggers database query."""
        # Setup mock cache to return None (cache miss)
        mock_cache.get.return_value = None

        PhotoFactory.create_photo_album(is_private=False)
        sitemap = PhotoAlbumSitemap()

        sitemap.items()

        # Verify cache.get was called
        mock_cache.get.assert_called_once_with("sitemap_photo_albums_v1")

        # Verify cache.set was called to store results
        mock_cache.set.assert_called_once()

        # Verify correct cache key and TTL
        call_args = mock_cache.set.call_args[0]
        actual_key = call_args[0]
        expected_key = "sitemap_photo_albums_v1"
        message = f"Cache key is '{actual_key}', expected '{expected_key}'"
        self.assertEqual(actual_key, expected_key, message)

        actual_ttl = call_args[2]
        expected_ttl = 43200  # 12 hours
        message = f"Cache TTL is {actual_ttl}, expected {expected_ttl}"
        self.assertEqual(actual_ttl, expected_ttl, message)

    @patch("photos.sitemaps.cache")
    def test_cache_hit_avoids_database_query(self, mock_cache):
        """Test that cache hit avoids database query."""
        # Create test albums
        album1 = PhotoFactory.create_photo_album(title="Cached 1", is_private=False)
        album2 = PhotoFactory.create_photo_album(title="Cached 2", is_private=False)

        # Setup mock cache to return cached albums
        mock_cache.get.return_value = [album1, album2]

        sitemap = PhotoAlbumSitemap()
        items = sitemap.items()

        # Verify cache.get was called
        mock_cache.get.assert_called_once_with("sitemap_photo_albums_v1")

        # Verify cache.set was NOT called (because we had a cache hit)
        mock_cache.set.assert_not_called()

        # Verify we got the cached items
        actual_count = len(items)
        expected_count = 2
        message = f"Got {actual_count} cached items, expected {expected_count}"
        self.assertEqual(actual_count, expected_count, message)
