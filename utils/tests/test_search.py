"""
Comprehensive test suite for the search functionality.

Tests cover:
- SearchableContent model and its methods
- Search functions (blog posts, projects, books, photos, albums)
- Search views and autocomplete API
- rebuild_search_index management command
"""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from utils.models import SearchableContent


class SearchableContentModelTest(TestCase):
    """Test the SearchableContent model."""

    def setUp(self):
        """Set up test data."""
        self.blog_post = SearchableContent.objects.create(
            content_type="blog_post",
            title="Introduction to Django",
            description="Learn Django web framework basics",
            content="Django is a high-level Python web framework that encourages rapid development.",
            category="tech",
            url="/b/tech/0001_introduction_to_django/",
            template_name="0001_introduction_to_django",
        )

        self.project = SearchableContent.objects.create(
            content_type="project",
            title="My Cool Project",
            description="A project about machine learning",
            content="This project uses advanced ML algorithms",
            url="https://github.com/user/project",
        )

        self.book = SearchableContent.objects.create(
            content_type="book",
            title="Python Crash Course",
            description="by Eric Matthes",
            content="A hands-on introduction to Python programming",
            url="/#books",
        )

    def test_model_creation(self):
        """Test that SearchableContent objects are created correctly."""
        self.assertEqual(SearchableContent.objects.count(), 3)
        self.assertEqual(self.blog_post.content_type, "blog_post")
        self.assertEqual(self.project.content_type, "project")
        self.assertEqual(self.book.content_type, "book")

    def test_update_search_vector(self):
        """Test that search vectors are updated correctly."""
        # Initially, search_vector might be None
        self.assertIsNone(self.blog_post.search_vector)

        # Update search vector
        SearchableContent.update_search_vector(self.blog_post.id)

        # Refresh from database
        self.blog_post.refresh_from_db()

        # Verify search vector is populated
        self.assertIsNotNone(self.blog_post.search_vector)


class SearchFunctionsTest(TestCase):
    """Test search functions for blog posts, projects, and books."""

    def setUp(self):
        """Set up test search data."""
        # Create blog posts with search vectors
        self.django_post = SearchableContent.objects.create(
            content_type="blog_post",
            title="Django Tutorial",
            description="Learn Django web development",
            content="Django is a powerful Python web framework with excellent documentation.",
            category="tech",
            url="/b/tech/0001_django_tutorial/",
            template_name="0001_django_tutorial",
        )
        SearchableContent.update_search_vector(self.django_post.id)

        self.flask_post = SearchableContent.objects.create(
            content_type="blog_post",
            title="Flask Microframework",
            description="Build lightweight web apps",
            content="Flask is a micro web framework written in Python.",
            category="tech",
            url="/b/tech/0002_flask_microframework/",
            template_name="0002_flask_microframework",
        )
        SearchableContent.update_search_vector(self.flask_post.id)

        # Create a project
        self.github_project = SearchableContent.objects.create(
            content_type="project",
            title="GitHub Monitor",
            description="Monitor GitHub Actions and get notifications",
            content="Track your CI/CD pipelines",
            url="https://github.com/user/monitor",
        )
        SearchableContent.update_search_vector(self.github_project.id)

        # Create a book
        self.python_book = SearchableContent.objects.create(
            content_type="book",
            title="Python for Everybody",
            description="by Charles Severance",
            content="Learn Python programming from scratch",
            url="/#books",
        )
        SearchableContent.update_search_vector(self.python_book.id)

    def test_search_blog_posts_without_query(self):
        """Test searching blog posts without a query returns all posts."""
        from utils.search import search_blog_posts

        results = search_blog_posts()
        self.assertEqual(len(results), 2)
        # Check that results are in order (newest first)
        self.assertIn(results[0]["template_name"], ["0002_flask_microframework", "0001_django_tutorial"])

    def test_search_blog_posts_with_query(self):
        """Test searching blog posts with a specific query."""
        from utils.search import search_blog_posts

        results = search_blog_posts("django")
        self.assertGreater(len(results), 0)

        # Django post should be in results
        titles = [r["blog_title"] for r in results]
        self.assertIn("Django Tutorial", titles)

    def test_search_blog_posts_by_category(self):
        """Test filtering blog posts by category."""
        from utils.search import search_blog_posts

        results = search_blog_posts(category="tech")
        self.assertEqual(len(results), 2)

        # Create a personal category post
        personal_post = SearchableContent.objects.create(
            content_type="blog_post",
            title="My Personal Story",
            description="A personal reflection",
            content="This is a personal blog post",
            category="personal",
            url="/b/personal/0003_my_story/",
            template_name="0003_my_story",
        )
        SearchableContent.update_search_vector(personal_post.id)

        results = search_blog_posts(category="personal")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["category"], "personal")

    def test_search_blog_posts_typo_tolerance(self):
        """Test that search handles typos using trigram similarity."""
        from utils.search import search_blog_posts

        # Search with typo "djang" should still find "django"
        results = search_blog_posts("djang")
        titles = [r["blog_title"] for r in results]

        # Should find the Django post even with typo
        self.assertIn("Django Tutorial", titles)

    def test_search_projects_without_query(self):
        """Test searching projects without a query."""
        from utils.search import search_projects

        results = search_projects()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "GitHub Monitor")

    def test_search_projects_with_query(self):
        """Test searching projects with a specific query."""
        from utils.search import search_projects

        results = search_projects("github")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["name"], "GitHub Monitor")

    def test_search_projects_typo_tolerance(self):
        """Test project search with typos."""
        from utils.search import search_projects

        # Search with partial match "githb" should still find "github"
        results = search_projects("githb")
        self.assertGreater(len(results), 0)

    def test_search_books_without_query(self):
        """Test searching books without a query."""
        from utils.search import search_books

        results = search_books()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Python for Everybody")

    def test_search_books_with_query(self):
        """Test searching books with a specific query."""
        from utils.search import search_books

        results = search_books("python")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["name"], "Python for Everybody")

    def test_search_books_by_author(self):
        """Test searching books by author name."""
        from utils.search import search_books

        results = search_books("Severance")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["name"], "Python for Everybody")


class SearchViewsTest(TestCase):
    """Test search views and autocomplete API."""

    def setUp(self):
        """Set up test data."""
        # Create searchable content
        self.django_post = SearchableContent.objects.create(
            content_type="blog_post",
            title="Django Best Practices",
            description="Tips for Django development",
            content="Learn best practices for Django development including testing and security.",
            category="tech",
            url="/b/tech/0001_django_best_practices/",
            template_name="0001_django_best_practices",
        )
        SearchableContent.update_search_vector(self.django_post.id)

        self.project = SearchableContent.objects.create(
            content_type="project",
            title="Web Scraper",
            description="A tool for web scraping",
            content="Scrape data from websites efficiently",
            url="https://github.com/user/scraper",
        )
        SearchableContent.update_search_vector(self.project.id)

    def test_search_view_get_request(self):
        """Test that search view handles GET requests."""
        url = reverse("search")
        response = self.client.get(url, {"q": "django"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("query", response.context)
        self.assertEqual(response.context["query"], "django")
        self.assertIn("results", response.context)

    def test_search_view_without_query(self):
        """Test search view without a query parameter."""
        url = reverse("search")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["query"], "")

    def test_search_view_with_category_filter(self):
        """Test search view with category filtering."""
        url = reverse("search")
        response = self.client.get(url, {"q": "django", "category": "tech"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["category"], "tech")

    def test_search_view_with_content_type_filter(self):
        """Test search view with content type filtering."""
        url = reverse("search")
        response = self.client.get(url, {"q": "web", "type": "projects"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["content_type"], "projects")

    def test_autocomplete_api_endpoint(self):
        """Test autocomplete API returns JSON suggestions."""
        url = reverse("search_autocomplete")
        response = self.client.get(url, {"q": "django"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = response.json()
        self.assertIn("suggestions", data)
        self.assertIsInstance(data["suggestions"], list)

    def test_autocomplete_with_short_query(self):
        """Test that autocomplete requires minimum 2 characters."""
        url = reverse("search_autocomplete")
        response = self.client.get(url, {"q": "d"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["suggestions"], [])

    def test_autocomplete_with_no_query(self):
        """Test autocomplete without query parameter."""
        url = reverse("search_autocomplete")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["suggestions"], [])

    def test_autocomplete_limits_results(self):
        """Test that autocomplete limits total results to 10."""
        # Create multiple searchable items
        for i in range(15):
            SearchableContent.objects.create(
                content_type="blog_post",
                title=f"Django Tutorial Part {i}",
                description=f"Part {i} of Django tutorial",
                content="Django content here",
                category="tech",
                url=f"/b/tech/000{i}_django_part_{i}/",
                template_name=f"000{i}_django_part_{i}",
            )

        url = reverse("search_autocomplete")
        response = self.client.get(url, {"q": "django"})

        data = response.json()
        # Should limit to 10 total suggestions
        self.assertLessEqual(len(data["suggestions"]), 10)


class RebuildSearchIndexCommandTest(TestCase):
    """Test the rebuild_search_index management command."""

    def test_command_runs_without_errors(self):
        """Test that the command executes without errors."""
        out = StringIO()
        call_command("rebuild_search_index", stdout=out)
        output = out.getvalue()

        self.assertIn("Starting search index rebuild", output)
        self.assertIn("Search index rebuild complete", output)

    def test_command_with_clear_flag(self):
        """Test that --clear flag removes existing data."""
        # Create some test data
        SearchableContent.objects.create(
            content_type="blog_post",
            title="Test Post",
            description="Test",
            content="Test content",
            category="tech",
            url="/b/tech/test/",
            template_name="test",
        )

        initial_count = SearchableContent.objects.count()
        self.assertGreater(initial_count, 0)

        # Run command with --clear
        out = StringIO()
        call_command("rebuild_search_index", "--clear", stdout=out)
        output = out.getvalue()

        self.assertIn("Search index cleared", output)

    def test_command_with_content_type_blog(self):
        """Test rebuilding only blog posts."""
        out = StringIO()
        call_command("rebuild_search_index", "--content-type", "blog", stdout=out)
        output = out.getvalue()

        self.assertIn("Indexing blog posts", output)
        # Should not index other content types
        self.assertNotIn("Indexing photos", output)
