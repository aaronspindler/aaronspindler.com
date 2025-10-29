from unittest.mock import patch

from django.test import TestCase

from blog.tests.factories import MockDataFactory
from blog.utils import get_all_blog_posts, get_blog_from_template_name


class BlogUtilsTest(TestCase):
    """Test blog utility functions."""

    @patch("blog.utils.render_to_string")
    def test_get_blog_from_template_name_with_category(self, mock_render):
        """Test getting blog data with category specified."""
        # Use consistent mock blog data structure
        mock_blog_data = MockDataFactory.get_mock_blog_data()
        mock_render.return_value = mock_blog_data["blog_content"]

        result = get_blog_from_template_name("0001_test_post", category="tech")

        self.assertEqual(result["entry_number"], "0001")
        self.assertEqual(result["template_name"], "0001_test_post")
        self.assertEqual(result["blog_title"], "0001 test post")
        self.assertEqual(result["blog_content"], mock_blog_data["blog_content"])
        self.assertEqual(result["category"], "tech")
        self.assertIn("github.com", result["github_link"])
        self.assertIn("tech/0001_test_post.html", result["github_link"])

        mock_render.assert_called_with("blog/tech/0001_test_post.html")

    def test_get_blog_from_template_name_without_category(self):
        """Test that category is required."""
        with self.assertRaises(ValueError) as context:
            get_blog_from_template_name("0001_test_post")

        self.assertIn("Category is required", str(context.exception))

    @patch("blog.utils.render_to_string")
    def test_get_blog_from_template_name_no_content(self, mock_render):
        """Test getting blog metadata without loading content."""
        result = get_blog_from_template_name("0001_test_post", load_content=False, category="tech")

        self.assertEqual(result["blog_content"], "")
        mock_render.assert_not_called()

    @patch("blog.utils.os.walk")
    @patch("blog.utils.os.path.relpath")
    def test_get_all_blog_posts(self, mock_relpath, mock_walk):
        """Test getting all blog posts from directory structure."""
        # Mock os.walk to return blog structure
        mock_walk.return_value = [
            ("/path/to/templates/blog", ["tech", "personal"], ["0001_root.html"]),
            (
                "/path/to/templates/blog/tech",
                [],
                ["0002_tech_post.html", "0003_another_tech.html"],
            ),
            ("/path/to/templates/blog/personal", [], ["0004_personal.html"]),
        ]

        # Mock os.path.relpath to return appropriate relative paths
        def mock_relpath_side_effect(path, start):
            if path == "/path/to/templates/blog":
                return "."
            elif path == "/path/to/templates/blog/tech":
                return "tech"
            elif path == "/path/to/templates/blog/personal":
                return "personal"
            return path

        mock_relpath.side_effect = mock_relpath_side_effect

        result = get_all_blog_posts()

        # Should only return categorized posts (root level posts are skipped)
        self.assertEqual(len(result), 3)

        # Check categorized posts
        tech_posts = [p for p in result if p["category"] == "tech"]
        self.assertEqual(len(tech_posts), 2)

        personal_posts = [p for p in result if p["category"] == "personal"]
        self.assertEqual(len(personal_posts), 1)

    @patch("blog.utils.os.walk")
    def test_get_all_blog_posts_nested_categories(self, mock_walk):
        """Test that nested category directories are handled correctly."""
        mock_walk.return_value = [
            ("/path/to/templates/blog", ["tech"], []),
            ("/path/to/templates/blog/tech", ["subcategory"], ["0001_tech.html"]),
            ("/path/to/templates/blog/tech/subcategory", [], ["0002_nested.html"]),
        ]

        # Mock os.path.relpath to return the expected relative paths
        with patch("blog.utils.os.path.relpath") as mock_relpath:
            mock_relpath.side_effect = [
                ".",  # Root directory
                "tech",  # Tech category
                "tech/subcategory",  # Nested category
            ]

            result = get_all_blog_posts()

            # First-level category
            tech_post = next(p for p in result if p["template_name"] == "0001_tech")
            self.assertEqual(tech_post["category"], "tech")

            # Nested category should use first-level category
            nested_post = next(p for p in result if p["template_name"] == "0002_nested")
            self.assertEqual(nested_post["category"], "tech")

    @patch("blog.utils.os.walk")
    @patch("blog.utils.os.path.relpath")
    def test_get_all_blog_posts_ignores_non_html(self, mock_relpath, mock_walk):
        """Test that non-HTML files are ignored and root posts are skipped."""
        mock_walk.return_value = [
            (
                "/path/to/templates/blog",
                ["tech"],
                [
                    "0001_root_post.html",  # This should be ignored (root level)
                    "README.md",
                    "style.css",
                    ".DS_Store",
                ],
            ),
            ("/path/to/templates/blog/tech", [], ["0002_tech_post.html", "README.md"]),
        ]

        def mock_relpath_side_effect(path, start):
            if path == "/path/to/templates/blog":
                return "."
            elif path == "/path/to/templates/blog/tech":
                return "tech"
            return path

        mock_relpath.side_effect = mock_relpath_side_effect

        result = get_all_blog_posts()

        # Only the tech post should be returned
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["template_name"], "0002_tech_post")
        self.assertEqual(result[0]["category"], "tech")
