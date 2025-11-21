from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from blog.tasks import generate_knowledge_graph_screenshot, rebuild_knowledge_graph


class BlogTasksTest(TestCase):
    """Test Celery tasks for blog app."""

    def setUp(self):
        cache.clear()

    @patch("blog.knowledge_graph.build_knowledge_graph")
    def test_rebuild_knowledge_graph_success(self, mock_build_graph):
        """Test successful knowledge graph rebuild task."""
        # Use MockDataFactory for consistent test data structure
        graph_data = {
            "nodes": [{"id": "test_post", "label": "Test Post"}],
            "edges": [{"source": "post1", "target": "post2", "type": "internal"}],
            "metrics": {"total_posts": 1, "total_internal_links": 1},
        }
        mock_build_graph.return_value = graph_data

        result = rebuild_knowledge_graph()

        self.assertEqual(result, graph_data)
        mock_build_graph.assert_called_once_with(force_refresh=False)

        # Check cache was set
        cached_data = cache.get("knowledge_graph_data")
        self.assertIsNotNone(cached_data)

    @patch("blog.knowledge_graph.build_knowledge_graph")
    def test_rebuild_knowledge_graph_failure(self, mock_build_graph):
        """Test knowledge graph rebuild task handles errors."""
        mock_build_graph.side_effect = Exception("Test error")

        result = rebuild_knowledge_graph()

        self.assertIsNone(result)

    @patch("django.core.management.call_command")
    def test_generate_knowledge_graph_screenshot_success(self, mock_call_command):
        """Test successful screenshot generation task."""
        result = generate_knowledge_graph_screenshot()

        self.assertEqual(result, "screenshot_generated")
        mock_call_command.assert_called_once_with(
            "generate_knowledge_graph_screenshot", "--url", "https://aaronspindler.com"
        )

    @patch("django.core.management.call_command")
    def test_generate_knowledge_graph_screenshot_failure(self, mock_call_command):
        """Test screenshot generation task handles errors."""
        mock_call_command.side_effect = RuntimeError("Screenshot error")

        with self.assertRaises(RuntimeError):
            generate_knowledge_graph_screenshot()


class ManagementCommandsTest(TestCase):
    """Test management commands for blog app."""

    def setUp(self):
        cache.clear()

    @patch("blog.management.commands.rebuild_knowledge_graph.build_knowledge_graph")
    def test_rebuild_knowledge_graph_command(self, mock_build):
        """Test rebuild_knowledge_graph management command."""
        # Use consistent mock data structure
        mock_build.return_value = {
            "nodes": [{"id": "test_post", "label": "Test Post"}],
            "edges": [{"source": "post1", "target": "post2", "type": "internal"}],
            "metrics": {
                "total_posts": 1,
                "total_internal_links": 1,
                "total_external_links": 0,
                "orphan_posts": [],
            },
        }

        out = StringIO()
        call_command("rebuild_knowledge_graph", stdout=out)

        output = out.getvalue()
        self.assertIn("Starting knowledge graph rebuild", output)
        self.assertIn("Rebuild complete", output)
        self.assertIn("1 posts", output)
        self.assertIn("1 internal links", output)
        mock_build.assert_called_with(force_refresh=True)

    @patch("blog.management.commands.rebuild_knowledge_graph.build_knowledge_graph")
    def test_rebuild_knowledge_graph_command_force(self, mock_build):
        """Test rebuild_knowledge_graph with force flag."""
        mock_build.return_value = {
            "nodes": [],
            "edges": [],
            "metrics": {
                "total_posts": 0,
                "total_internal_links": 0,
                "total_external_links": 0,
            },
        }

        out = StringIO()
        call_command("rebuild_knowledge_graph", "--force", stdout=out)

        mock_build.assert_called_with(force_refresh=True)

    @patch("django.test.Client")
    @patch("blog.management.commands.rebuild_knowledge_graph.build_knowledge_graph")
    def test_rebuild_knowledge_graph_command_test_api(self, mock_build, mock_client_class):
        """Test rebuild_knowledge_graph with API test flag."""
        mock_build.return_value = {"nodes": [], "edges": [], "metrics": {}}

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        out = StringIO()
        call_command("rebuild_knowledge_graph", "--test-api", stdout=out)

        output = out.getvalue()
        self.assertIn("API test passed", output)
        mock_client.get.assert_called_with("/api/knowledge-graph/")

    @patch("asyncio.run")
    @patch("blog.knowledge_graph.build_knowledge_graph")
    def test_generate_knowledge_graph_screenshot_command(self, mock_build_graph, mock_asyncio_run):
        """Test generate_knowledge_graph_screenshot command."""
        # Mock the screenshot generation to return fake data without launching pyppeteer
        mock_asyncio_run.return_value = b"fake_screenshot_data"

        # Mock the knowledge graph build
        mock_build_graph.return_value = {
            "nodes": [{"id": "test", "label": "Test"}],
            "edges": [],
            "metrics": {},
        }

        out = StringIO()
        call_command("generate_knowledge_graph_screenshot", stdout=out)

        output = out.getvalue()
        self.assertIn("Starting knowledge graph screenshot generation", output)
        self.assertIn("Successfully generated", output)
        # Verify asyncio.run was called (pyppeteer is async)
        self.assertTrue(mock_asyncio_run.called)

    @patch("asyncio.run")
    @patch("blog.knowledge_graph.build_knowledge_graph")
    def test_generate_knowledge_graph_screenshot_command_custom_url(self, mock_build_graph, mock_asyncio_run):
        """Test generate_knowledge_graph_screenshot command with custom URL."""
        # Mock the screenshot generation
        mock_asyncio_run.return_value = b"fake_screenshot_data"

        # Mock the knowledge graph build
        mock_build_graph.return_value = {
            "nodes": [{"id": "test", "label": "Test"}],
            "edges": [],
            "metrics": {},
        }

        out = StringIO()
        call_command("generate_knowledge_graph_screenshot", "--url", "https://example.com", stdout=out)

        output = out.getvalue()
        self.assertIn("Starting knowledge graph screenshot generation", output)
        self.assertIn("Successfully generated", output)
        # Verify asyncio.run was called (pyppeteer is async)
        self.assertTrue(mock_asyncio_run.called)


class TaskIntegrationTest(TestCase):
    """Test integration of tasks with cache and models."""

    def setUp(self):
        cache.clear()

    @patch("blog.knowledge_graph.build_knowledge_graph")
    def test_rebuild_knowledge_graph_cache_integration(self, mock_build_graph):
        """Test that rebuild task properly sets cache."""
        test_data = {
            "nodes": [{"id": "post1", "label": "Post 1"}],
            "edges": [{"source": "post1", "target": "post2"}],
            "metrics": {"total_posts": 2},
        }

        mock_build_graph.return_value = test_data

        # Run the task
        result = rebuild_knowledge_graph()

        self.assertEqual(result, test_data)

        # Check cache
        cached_data = cache.get("knowledge_graph_data")
        self.assertEqual(cached_data, test_data)

    @patch("blog.tasks.logger")
    @patch("blog.knowledge_graph.build_knowledge_graph")
    def test_task_logging(self, mock_build_graph, mock_logger):
        """Test that tasks log appropriately."""
        mock_build_graph.return_value = {"nodes": [], "edges": []}

        rebuild_knowledge_graph()

        mock_logger.info.assert_called_with("Knowledge graph rebuilt and cached successfully")

        # Test error logging
        mock_build_graph.side_effect = Exception("Error")
        rebuild_knowledge_graph()

        self.assertTrue(mock_logger.error.called)
        error_call = mock_logger.error.call_args[0][0]
        self.assertIn("Error rebuilding knowledge graph", error_call)
