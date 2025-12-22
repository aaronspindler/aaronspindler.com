from unittest.mock import MagicMock, patch

from django.test import TestCase

from pages.tasks import rebuild_and_cache_sitemap


class RebuildAndCacheSitemapTaskTest(TestCase):
    @patch("pages.tasks.Client")
    @patch("pages.tasks.logger")
    def test_rebuild_and_cache_sitemap_success(self, mock_logger, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response

        with patch("config.sitemaps.sitemaps", {"static": None, "blog": None}):
            result = rebuild_and_cache_sitemap()

        mock_client.get.assert_any_call("/sitemap.xml")

        mock_client.get.assert_any_call("/sitemap-static.xml")
        mock_client.get.assert_any_call("/sitemap-blog.xml")

        mock_logger.info.assert_any_call("Main sitemap index cached successfully")
        mock_logger.info.assert_any_call("Sitemap section 'static' cached successfully")
        mock_logger.info.assert_any_call("Sitemap section 'blog' cached successfully")
        mock_logger.info.assert_any_call("All sitemaps rebuilt and cached successfully")

        self.assertTrue(result)

    @patch("pages.tasks.Client")
    @patch("pages.tasks.logger")
    def test_rebuild_and_cache_sitemap_partial_failure(self, mock_logger, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        responses = [
            MagicMock(status_code=200),  # Main sitemap
            MagicMock(status_code=404),  # Static section fails
            MagicMock(status_code=200),  # Blog section succeeds
        ]
        mock_client.get.side_effect = responses

        with patch("config.sitemaps.sitemaps", {"static": None, "blog": None}):
            result = rebuild_and_cache_sitemap()

        mock_logger.warning.assert_any_call("Failed to cache sitemap section 'static': 404")

        self.assertTrue(result)

    @patch("pages.tasks.Client")
    @patch("pages.tasks.logger")
    def test_rebuild_and_cache_sitemap_exception(self, mock_logger, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Make client.get raise an exception
        mock_client.get.side_effect = Exception("Connection error")

        result = rebuild_and_cache_sitemap()

        # Should log error
        mock_logger.error.assert_called()
        error_message = mock_logger.error.call_args[0][0]
        self.assertIn("Error rebuilding and caching sitemaps", error_message)

        self.assertFalse(result)

    @patch("pages.tasks.Client")
    @patch("pages.tasks.logger")
    def test_rebuild_and_cache_sitemap_empty_sitemaps(self, mock_logger, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response

        with patch("config.sitemaps.sitemaps", {}):
            result = rebuild_and_cache_sitemap()

        self.assertEqual(mock_client.get.call_count, 1)
        mock_client.get.assert_called_with("/sitemap.xml")

        self.assertTrue(result)

    @patch("pages.tasks.Client")
    @patch("pages.tasks.logger")
    def test_rebuild_and_cache_sitemap_many_sections(self, mock_logger, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response

        sections = {
            "static": None,
            "blog": None,
            "photos": None,
            "projects": None,
        }

        with patch("config.sitemaps.sitemaps", sections):
            result = rebuild_and_cache_sitemap()

        self.assertEqual(mock_client.get.call_count, 5)

        for section in sections.keys():
            mock_client.get.assert_any_call(f"/sitemap-{section}.xml")

        self.assertTrue(result)

    def test_task_decorator(self):
        from pages.tasks import rebuild_and_cache_sitemap

        self.assertTrue(hasattr(rebuild_and_cache_sitemap, "delay"))
        self.assertTrue(hasattr(rebuild_and_cache_sitemap, "apply_async"))

    @patch("pages.tasks.Client")
    def test_rebuild_and_cache_sitemap_url_format(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response

        with patch("config.sitemaps.sitemaps", {"test_section": None}):
            rebuild_and_cache_sitemap()

        # Check URL format
        calls = mock_client.get.call_args_list
        urls = [call[0][0] for call in calls]

        self.assertIn("/sitemap.xml", urls)
        self.assertIn("/sitemap-test_section.xml", urls)

        for url in urls:
            self.assertTrue(url.startswith("/"))

        for url in urls:
            self.assertTrue(url.endswith(".xml"))
