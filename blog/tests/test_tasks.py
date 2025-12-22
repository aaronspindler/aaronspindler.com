from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from blog.tasks import generate_knowledge_graph_screenshot, rebuild_knowledge_graph


class BlogTasksTest(TestCase):
    def setUp(self):
        cache.clear()

    @patch("blog.knowledge_graph.build_knowledge_graph")
    def test_rebuild_knowledge_graph_success(self, mock_build_graph):
        graph_data = {
            "nodes": [{"id": "test_post", "label": "Test Post"}],
            "edges": [{"source": "post1", "target": "post2", "type": "internal"}],
            "metrics": {"total_posts": 1, "total_internal_links": 1},
        }
        mock_build_graph.return_value = graph_data

        result = rebuild_knowledge_graph()

        self.assertEqual(result, graph_data)
        mock_build_graph.assert_called_once_with(force_refresh=False)

        cached_data = cache.get("knowledge_graph_data")
        self.assertIsNotNone(cached_data)

    @patch("blog.knowledge_graph.build_knowledge_graph")
    def test_rebuild_knowledge_graph_failure(self, mock_build_graph):
        mock_build_graph.side_effect = RuntimeError("Test error")

        # Task has autoretry configured, so calling it raises Retry exception
        # Use .run() to bypass Celery's retry machinery and test the error handling
        with self.assertRaises(RuntimeError) as context:
            rebuild_knowledge_graph.run(force_refresh=False)

        actual_message = str(context.exception)
        expected_message = "Test error"
        message = f"Expected '{expected_message}', got '{actual_message}'"
        self.assertEqual(actual_message, expected_message, message)

    @patch("django.core.management.call_command")
    def test_generate_knowledge_graph_screenshot_success(self, mock_call_command):
        result = generate_knowledge_graph_screenshot()

        self.assertEqual(result, "screenshot_generated")
        mock_call_command.assert_called_once_with(
            "generate_knowledge_graph_screenshot", "--url", "https://aaronspindler.com"
        )

    @patch("django.core.management.call_command")
    def test_generate_knowledge_graph_screenshot_failure(self, mock_call_command):
        mock_call_command.side_effect = RuntimeError("Screenshot error")

        with self.assertRaises(RuntimeError):
            generate_knowledge_graph_screenshot()


class ManagementCommandsTest(TestCase):
    def setUp(self):
        cache.clear()

    @patch("blog.management.commands.rebuild_knowledge_graph.build_knowledge_graph")
    def test_rebuild_knowledge_graph_command(self, mock_build):
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
        mock_asyncio_run.return_value = b"fake_screenshot_data"

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
        self.assertTrue(mock_asyncio_run.called)

    @patch("asyncio.run")
    @patch("blog.knowledge_graph.build_knowledge_graph")
    def test_generate_knowledge_graph_screenshot_command_custom_url(self, mock_build_graph, mock_asyncio_run):
        mock_asyncio_run.return_value = b"fake_screenshot_data"

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
        self.assertTrue(mock_asyncio_run.called)


class TaskIntegrationTest(TestCase):
    def setUp(self):
        cache.clear()

    @patch("blog.knowledge_graph.build_knowledge_graph")
    def test_rebuild_knowledge_graph_cache_integration(self, mock_build_graph):
        test_data = {
            "nodes": [{"id": "post1", "label": "Post 1"}],
            "edges": [{"source": "post1", "target": "post2"}],
            "metrics": {"total_posts": 2},
        }

        mock_build_graph.return_value = test_data

        result = rebuild_knowledge_graph()

        self.assertEqual(result, test_data)

        cached_data = cache.get("knowledge_graph_data")
        self.assertEqual(cached_data, test_data)

    @patch("blog.tasks.logger")
    @patch("blog.knowledge_graph.build_knowledge_graph")
    def test_task_logging(self, mock_build_graph, mock_logger):
        mock_build_graph.return_value = {"nodes": [], "edges": []}

        rebuild_knowledge_graph.run(force_refresh=False)

        mock_logger.info.assert_called_with("Knowledge graph rebuilt and cached successfully")

        # Test error logging - use .run() and expect exception
        mock_build_graph.side_effect = RuntimeError("Error")
        with self.assertRaises(RuntimeError):
            rebuild_knowledge_graph.run(force_refresh=False)

        self.assertTrue(mock_logger.error.called)
        error_call = mock_logger.error.call_args[0][0]
        self.assertIn("Error rebuilding knowledge graph", error_call)
