from django.test import TestCase
from django.core.management import call_command
from django.core.cache import cache
from unittest.mock import patch, MagicMock
from blog.tasks import rebuild_knowledge_graph, generate_knowledge_graph_screenshot
from tests.factories import MockDataFactory
from io import StringIO
import logging


class BlogTasksTest(TestCase):
    """Test Celery tasks for blog app."""

    def setUp(self):
        cache.clear()

    @patch('blog.tasks.KnowledgeGraph')
    def test_rebuild_knowledge_graph_success(self, mock_kg_class):
        """Test successful knowledge graph rebuild task."""
        mock_kg = MagicMock()
        # Use MockDataFactory for consistent test data structure
        mock_kg.generate_graph_data.return_value = {
            'nodes': [{'id': 'test_post', 'label': 'Test Post'}],
            'edges': [{'source': 'post1', 'target': 'post2', 'type': 'internal'}],
            'metrics': {'total_posts': 1, 'total_internal_links': 1}
        }
        mock_kg_class.return_value = mock_kg
        
        result = rebuild_knowledge_graph()
        
        self.assertTrue(result)
        mock_kg.generate_graph_data.assert_called_once()
        
        # Check cache was set
        cached_data = cache.get('knowledge_graph_data')
        self.assertIsNotNone(cached_data)

    @patch('blog.tasks.KnowledgeGraph')
    def test_rebuild_knowledge_graph_failure(self, mock_kg_class):
        """Test knowledge graph rebuild task handles errors."""
        mock_kg = MagicMock()
        mock_kg.generate_graph_data.side_effect = Exception('Test error')
        mock_kg_class.return_value = mock_kg
        
        result = rebuild_knowledge_graph()
        
        self.assertFalse(result)

    @patch('blog.tasks.KnowledgeGraph')
    def test_generate_knowledge_graph_screenshot_success(self, mock_kg_class):
        """Test successful screenshot generation task."""
        mock_kg = MagicMock()
        mock_kg.generate_screenshot.return_value = '/path/to/screenshot.png'
        mock_kg_class.return_value = mock_kg
        
        result = generate_knowledge_graph_screenshot()
        
        self.assertEqual(result, '/path/to/screenshot.png')
        mock_kg.generate_screenshot.assert_called_once()

    @patch('blog.tasks.KnowledgeGraph')
    def test_generate_knowledge_graph_screenshot_failure(self, mock_kg_class):
        """Test screenshot generation task handles errors."""
        mock_kg = MagicMock()
        mock_kg.generate_screenshot.side_effect = Exception('Screenshot error')
        mock_kg_class.return_value = mock_kg
        
        result = generate_knowledge_graph_screenshot()
        
        self.assertIsNone(result)


class ManagementCommandsTest(TestCase):
    """Test management commands for blog app."""

    def setUp(self):
        cache.clear()

    @patch('blog.management.commands.rebuild_knowledge_graph.build_knowledge_graph')
    def test_rebuild_knowledge_graph_command(self, mock_build):
        """Test rebuild_knowledge_graph management command."""
        # Use consistent mock data structure
        mock_build.return_value = {
            'nodes': [{'id': 'test_post', 'label': 'Test Post'}],
            'edges': [{'source': 'post1', 'target': 'post2', 'type': 'internal'}],
            'metrics': {
                'total_posts': 1,
                'total_internal_links': 1,
                'total_external_links': 0,
                'orphan_posts': []
            }
        }
        
        out = StringIO()
        call_command('rebuild_knowledge_graph', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Starting knowledge graph rebuild', output)
        self.assertIn('Rebuild complete', output)
        self.assertIn('1 posts', output)
        self.assertIn('1 internal links', output)
        mock_build.assert_called_with(force_refresh=True)

    @patch('blog.management.commands.rebuild_knowledge_graph.build_knowledge_graph')
    def test_rebuild_knowledge_graph_command_force(self, mock_build):
        """Test rebuild_knowledge_graph with force flag."""
        mock_build.return_value = {
            'nodes': [],
            'edges': [],
            'metrics': {
                'total_posts': 0,
                'total_internal_links': 0,
                'total_external_links': 0
            }
        }
        
        out = StringIO()
        call_command('rebuild_knowledge_graph', '--force', stdout=out)
        
        mock_build.assert_called_with(force_refresh=True)

    @patch('blog.management.commands.rebuild_knowledge_graph.Client')
    @patch('blog.management.commands.rebuild_knowledge_graph.build_knowledge_graph')
    def test_rebuild_knowledge_graph_command_test_api(self, mock_build, mock_client_class):
        """Test rebuild_knowledge_graph with API test flag."""
        mock_build.return_value = {
            'nodes': [],
            'edges': [],
            'metrics': {}
        }
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        out = StringIO()
        call_command('rebuild_knowledge_graph', '--test-api', stdout=out)
        
        output = out.getvalue()
        self.assertIn('API test passed', output)
        mock_client.get.assert_called_with('/api/knowledge-graph/')

    @patch('blog.management.commands.generate_knowledge_graph_screenshot.sync_playwright')
    def test_generate_knowledge_graph_screenshot_command(self, mock_playwright):
        """Test generate_knowledge_graph_screenshot command."""
        # Mock Playwright
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_element = MagicMock()
        
        mock_playwright_instance = MagicMock()
        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.query_selector.return_value = mock_element
        mock_element.screenshot.return_value = b'fake_screenshot_data'
        
        # Mock file operations
        with patch('builtins.open', MagicMock()):
            out = StringIO()
            call_command('generate_knowledge_graph_screenshot', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Starting knowledge graph screenshot generation', output)
        self.assertIn('Successfully generated', output)

    @patch('blog.management.commands.generate_knowledge_graph_screenshot.sync_playwright')
    def test_generate_knowledge_graph_screenshot_custom_options(self, mock_playwright):
        """Test screenshot command with custom options."""
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_context = MagicMock()
        
        mock_playwright_instance = MagicMock()
        mock_playwright.return_value.__enter__.return_value = mock_playwright_instance
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.screenshot.return_value = b'fake_screenshot_data'
        
        with patch('builtins.open', MagicMock()):
            out = StringIO()
            call_command(
                'generate_knowledge_graph_screenshot',
                '--width=1920',
                '--height=1080',
                '--device-scale-factor=1.5',
                '--wait-time=5000',
                '--quality=90',
                '--full-page',
                '--transparent',
                stdout=out
            )
        
        # Verify viewport settings
        mock_browser.new_context.assert_called_once()
        context_args = mock_browser.new_context.call_args[1]
        self.assertEqual(context_args['viewport']['width'], 1920)
        self.assertEqual(context_args['viewport']['height'], 1080)
        self.assertEqual(context_args['device_scale_factor'], 1.5)

    @patch('django_celery_beat.models.CrontabSchedule')
    @patch('django_celery_beat.models.PeriodicTask')
    def test_setup_periodic_tasks_command(self, mock_periodic_task, mock_crontab):
        """Test setup_periodic_tasks management command."""
        # Mock the model operations
        mock_schedule = MagicMock()
        mock_crontab.objects.get_or_create.return_value = (mock_schedule, True)
        mock_periodic_task.objects.update_or_create.return_value = (MagicMock(), True)
        
        out = StringIO()
        call_command('setup_periodic_tasks', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Successfully created periodic task', output)
        self.assertIn('Rebuild and cache sitemap daily', output)
        self.assertIn('Rebuild knowledge graph cache', output)
        self.assertIn('Generate knowledge graph screenshot', output)
        
        # Verify tasks were created
        self.assertTrue(mock_periodic_task.objects.update_or_create.called)
        # Should create 3 tasks (sitemap, knowledge graph, screenshot)
        self.assertEqual(mock_periodic_task.objects.update_or_create.call_count, 3)


class TaskIntegrationTest(TestCase):
    """Test integration of tasks with cache and models."""

    def setUp(self):
        cache.clear()

    @patch('blog.tasks.KnowledgeGraph')
    def test_rebuild_knowledge_graph_cache_integration(self, mock_kg_class):
        """Test that rebuild task properly sets cache."""
        test_data = {
            'nodes': [{'id': 'post1', 'label': 'Post 1'}],
            'edges': [{'source': 'post1', 'target': 'post2'}],
            'metrics': {'total_posts': 2}
        }
        
        mock_kg = MagicMock()
        mock_kg.generate_graph_data.return_value = test_data
        mock_kg_class.return_value = mock_kg
        
        # Run the task
        result = rebuild_knowledge_graph()
        
        self.assertTrue(result)
        
        # Check cache
        cached_data = cache.get('knowledge_graph_data')
        self.assertEqual(cached_data, test_data)

    @patch('blog.tasks.logger')
    @patch('blog.tasks.KnowledgeGraph')
    def test_task_logging(self, mock_kg_class, mock_logger):
        """Test that tasks log appropriately."""
        mock_kg = MagicMock()
        mock_kg.generate_graph_data.return_value = {'nodes': [], 'edges': []}
        mock_kg_class.return_value = mock_kg
        
        rebuild_knowledge_graph()
        
        mock_logger.info.assert_called_with(
            "Knowledge graph rebuilt and cached successfully"
        )
        
        # Test error logging
        mock_kg.generate_graph_data.side_effect = Exception('Error')
        rebuild_knowledge_graph()
        
        self.assertTrue(mock_logger.error.called)
        error_call = mock_logger.error.call_args[0][0]
        self.assertIn('Error rebuilding knowledge graph', error_call)
