from django.test import TestCase
from unittest.mock import patch, MagicMock
from pages.tasks import rebuild_and_cache_sitemap


class RebuildAndCacheSitemapTaskTest(TestCase):
    """Test the rebuild_and_cache_sitemap Celery task."""
    
    @patch('pages.tasks.Client')
    @patch('pages.tasks.logger')
    def test_rebuild_and_cache_sitemap_success(self, mock_logger, mock_client_class):
        """Test successful sitemap rebuilding and caching."""
        # Setup mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock successful responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        
        # Mock sitemaps configuration
        with patch('config.sitemaps.sitemaps', {'static': None, 'blog': None}):
            result = rebuild_and_cache_sitemap()
            
        # Verify the main sitemap was requested
        mock_client.get.assert_any_call('/sitemap.xml')
        
        # Verify section sitemaps were requested
        mock_client.get.assert_any_call('/sitemap-static.xml')
        mock_client.get.assert_any_call('/sitemap-blog.xml')
        
        # Verify success was logged
        mock_logger.info.assert_any_call("Main sitemap index cached successfully")
        mock_logger.info.assert_any_call("Sitemap section 'static' cached successfully")
        mock_logger.info.assert_any_call("Sitemap section 'blog' cached successfully")
        mock_logger.info.assert_any_call("All sitemaps rebuilt and cached successfully")
        
        # Task should return True
        self.assertTrue(result)
        
    @patch('pages.tasks.Client')
    @patch('pages.tasks.logger')
    def test_rebuild_and_cache_sitemap_partial_failure(self, mock_logger, mock_client_class):
        """Test sitemap rebuilding with some sections failing."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock mixed responses
        responses = [
            MagicMock(status_code=200),  # Main sitemap
            MagicMock(status_code=404),  # Static section fails
            MagicMock(status_code=200),  # Blog section succeeds
        ]
        mock_client.get.side_effect = responses
        
        with patch('config.sitemaps.sitemaps', {'static': None, 'blog': None}):
            result = rebuild_and_cache_sitemap()
            
        # Verify warnings for failures
        mock_logger.warning.assert_any_call(
            "Failed to cache sitemap section 'static': 404"
        )
        
        # Still returns True even with partial failure
        self.assertTrue(result)
        
    @patch('pages.tasks.Client')
    @patch('pages.tasks.logger')
    def test_rebuild_and_cache_sitemap_exception(self, mock_logger, mock_client_class):
        """Test sitemap rebuilding with exception handling."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Make client.get raise an exception
        mock_client.get.side_effect = Exception('Connection error')
        
        result = rebuild_and_cache_sitemap()
        
        # Should log error
        mock_logger.error.assert_called()
        error_message = mock_logger.error.call_args[0][0]
        self.assertIn('Error rebuilding and caching sitemaps', error_message)
        
        # Task should return False
        self.assertFalse(result)
        
    @patch('pages.tasks.Client')
    @patch('pages.tasks.logger')
    def test_rebuild_and_cache_sitemap_empty_sitemaps(self, mock_logger, mock_client_class):
        """Test sitemap rebuilding with no sitemap sections."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        
        # Empty sitemaps dictionary
        with patch('config.sitemaps.sitemaps', {}):
            result = rebuild_and_cache_sitemap()
            
        # Should only request main sitemap
        self.assertEqual(mock_client.get.call_count, 1)
        mock_client.get.assert_called_with('/sitemap.xml')
        
        self.assertTrue(result)
        
    @patch('pages.tasks.Client')
    @patch('pages.tasks.logger')
    def test_rebuild_and_cache_sitemap_many_sections(self, mock_logger, mock_client_class):
        """Test sitemap rebuilding with many sections."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        
        # Multiple sitemap sections
        sections = {
            'static': None,
            'blog': None,
            'photos': None,
            'projects': None,
        }
        
        with patch('config.sitemaps.sitemaps', sections):
            result = rebuild_and_cache_sitemap()
            
        # Should request main + all sections
        self.assertEqual(mock_client.get.call_count, 5)
        
        # Verify each section was requested
        for section in sections.keys():
            mock_client.get.assert_any_call(f'/sitemap-{section}.xml')
            
        self.assertTrue(result)
        
    def test_task_decorator(self):
        """Test that the task is properly decorated with @shared_task."""
        from pages.tasks import rebuild_and_cache_sitemap
        
        # Verify the function has Celery task attributes
        self.assertTrue(hasattr(rebuild_and_cache_sitemap, 'delay'))
        self.assertTrue(hasattr(rebuild_and_cache_sitemap, 'apply_async'))
        
    @patch('pages.tasks.Client')
    def test_rebuild_and_cache_sitemap_url_format(self, mock_client_class):
        """Test that sitemap URLs are formatted correctly."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        
        with patch('config.sitemaps.sitemaps', {'test_section': None}):
            rebuild_and_cache_sitemap()
            
        # Check URL format
        calls = mock_client.get.call_args_list
        urls = [call[0][0] for call in calls]
        
        self.assertIn('/sitemap.xml', urls)
        self.assertIn('/sitemap-test_section.xml', urls)
        
        # URLs should start with /
        for url in urls:
            self.assertTrue(url.startswith('/'))
            
        # URLs should end with .xml
        for url in urls:
            self.assertTrue(url.endswith('.xml'))
