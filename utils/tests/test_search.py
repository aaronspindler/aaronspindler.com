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

from pages.utils import get_books, get_projects
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

    def test_model_str_representation(self):
        """Test the string representation of SearchableContent."""
        self.assertEqual(str(self.blog_post), "Blog Post: Introduction to Django")
        self.assertEqual(str(self.project), "Project: My Cool Project")
        self.assertEqual(str(self.book), "Book: Python Crash Course")

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

    def test_ordering(self):
        """Test that SearchableContent is ordered by created_at descending."""
        queryset = SearchableContent.objects.all()
        # Book was created last, so it should be first in the queryset
        self.assertEqual(queryset[0].id, self.book.id)

    def test_content_type_filtering(self):
        """Test filtering by content type."""
        blog_posts = SearchableContent.objects.filter(content_type="blog_post")
        self.assertEqual(blog_posts.count(), 1)
        self.assertEqual(blog_posts.first().title, "Introduction to Django")

        projects = SearchableContent.objects.filter(content_type="project")
        self.assertEqual(projects.count(), 1)

        books = SearchableContent.objects.filter(content_type="book")
        self.assertEqual(books.count(), 1)

    def test_category_filtering(self):
        """Test filtering by category."""
        tech_posts = SearchableContent.objects.filter(category="tech")
        self.assertEqual(tech_posts.count(), 1)
        self.assertEqual(tech_posts.first().title, "Introduction to Django")

    def test_template_name_filtering(self):
        """Test filtering by template name."""
        post = SearchableContent.objects.filter(template_name="0001_introduction_to_django")
        self.assertEqual(post.count(), 1)
        self.assertEqual(post.first().title, "Introduction to Django")


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

    def test_empty_search_query(self):
        """Test that empty queries return all results."""
        from utils.search import search_blog_posts, search_books, search_projects

        blog_results = search_blog_posts("")
        self.assertEqual(len(blog_results), 2)

        project_results = search_projects("")
        self.assertEqual(len(project_results), 1)

        book_results = search_books("")
        self.assertEqual(len(book_results), 1)


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

    def test_autocomplete_suggestion_structure(self):
        """Test that autocomplete suggestions have correct structure."""
        url = reverse("search_autocomplete")
        response = self.client.get(url, {"q": "django"})

        data = response.json()
        if len(data["suggestions"]) > 0:
            suggestion = data["suggestions"][0]
            self.assertIn("title", suggestion)
            self.assertIn("type", suggestion)
            self.assertIn("url", suggestion)

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

    def test_command_with_content_type_projects(self):
        """Test rebuilding only projects."""
        out = StringIO()
        call_command("rebuild_search_index", "--content-type", "projects", stdout=out)
        output = out.getvalue()

        self.assertIn("Indexing projects", output)
        # Should not index other content types
        self.assertNotIn("Indexing blog posts", output)

    def test_command_with_content_type_books(self):
        """Test rebuilding only books."""
        out = StringIO()
        call_command("rebuild_search_index", "--content-type", "books", stdout=out)
        output = out.getvalue()

        self.assertIn("Indexing books", output)

    def test_command_indexes_projects_from_utils(self):
        """Test that projects are indexed from pages.utils.get_projects()."""
        out = StringIO()
        call_command("rebuild_search_index", "--clear", "--content-type", "projects", stdout=out)

        # Should have indexed all projects from get_projects()
        projects_count = SearchableContent.objects.filter(content_type="project").count()
        expected_count = len(get_projects())
        self.assertEqual(projects_count, expected_count)

    def test_command_indexes_books_from_utils(self):
        """Test that books are indexed from pages.utils.get_books()."""
        out = StringIO()
        call_command("rebuild_search_index", "--clear", "--content-type", "books", stdout=out)

        # Should have indexed all books from get_books()
        books_count = SearchableContent.objects.filter(content_type="book").count()
        expected_count = len(get_books())
        self.assertEqual(books_count, expected_count)

    def test_command_shows_statistics(self):
        """Test that command shows statistics at the end."""
        out = StringIO()
        call_command("rebuild_search_index", stdout=out)
        output = out.getvalue()

        self.assertIn("Search Index Statistics:", output)
        self.assertIn("Total:", output)
        self.assertIn("Blog Posts:", output)
        self.assertIn("Projects:", output)
        self.assertIn("Books:", output)


class PhotoSearchTest(TestCase):
    """Test search functionality for photos and albums."""

    def setUp(self):
        """Set up test photo data."""
        # Note: Photo creation requires image files, so we'll test what we can
        pass

    def test_search_photos_function_exists(self):
        """Test that search_photos function is importable."""
        from utils.search import search_photos

        # Function should be callable
        self.assertTrue(callable(search_photos))

    def test_search_photo_albums_function_exists(self):
        """Test that search_photo_albums function is importable."""
        from utils.search import search_photo_albums

        # Function should be callable
        self.assertTrue(callable(search_photo_albums))


class SearchIntegrationTest(TestCase):
    """Integration tests for full search workflow."""

    def test_end_to_end_search_workflow(self):
        """Test complete search workflow from indexing to searching."""
        # 1. Index some content
        blog_post = SearchableContent.objects.create(
            content_type="blog_post",
            title="Machine Learning Tutorial",
            description="Introduction to ML",
            content="Machine learning is a subset of artificial intelligence",
            category="tech",
            url="/b/tech/ml_tutorial/",
            template_name="ml_tutorial",
        )
        SearchableContent.update_search_vector(blog_post.id)

        # 2. Search for it
        from utils.search import search_blog_posts

        results = search_blog_posts("machine learning")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["template_name"], "ml_tutorial")

        # 3. Test via API endpoint
        url = reverse("search_autocomplete")
        response = self.client.get(url, {"q": "machine"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data["suggestions"]), 0)

    def test_combined_search_across_content_types(self):
        """Test searching across multiple content types."""
        # Create different content types with same keyword
        SearchableContent.objects.create(
            content_type="blog_post",
            title="Python Programming",
            description="Learn Python",
            content="Python is great",
            category="tech",
            url="/b/tech/python/",
            template_name="python",
        )

        SearchableContent.objects.create(
            content_type="project",
            title="Python Automation",
            description="Automate tasks with Python",
            content="Python scripts",
            url="https://github.com/user/automation",
        )

        SearchableContent.objects.create(
            content_type="book",
            title="Learning Python",
            description="by Mark Lutz",
            content="Comprehensive Python guide",
            url="/#books",
        )

        # Update search vectors
        for obj in SearchableContent.objects.all():
            SearchableContent.update_search_vector(obj.id)

        # Search via view
        url = reverse("search")
        response = self.client.get(url, {"q": "python"})

        self.assertEqual(response.status_code, 200)
        results = response.context["results"]

        # Should find results in all content types
        self.assertGreater(len(results["blog_posts"]), 0)
        self.assertGreater(len(results["projects"]), 0)
        self.assertGreater(len(results["books"]), 0)

    def test_search_relevance_scoring(self):
        """Test that search results are ordered by relevance."""
        # Create posts with different relevance
        high_relevance = SearchableContent.objects.create(
            content_type="blog_post",
            title="Django Framework",  # "Django" in title - high relevance
            description="Django info",
            content="Django Django Django",  # Multiple mentions
            category="tech",
            url="/b/tech/django_framework/",
            template_name="django_framework",
        )
        SearchableContent.update_search_vector(high_relevance.id)

        low_relevance = SearchableContent.objects.create(
            content_type="blog_post",
            title="Web Development",  # "Django" not in title
            description="Web dev info",
            content="Some Django mention here.",  # Single mention
            category="tech",
            url="/b/tech/web_dev/",
            template_name="web_dev",
        )
        SearchableContent.update_search_vector(low_relevance.id)

        from utils.search import search_blog_posts

        results = search_blog_posts("django")

        # High relevance post should appear first
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["template_name"], "django_framework")


class UtilsFunctionsTest(TestCase):
    """Test utility functions for projects and books."""

    def test_get_projects_returns_list(self):
        """Test that get_projects() returns a list."""
        projects = get_projects()
        self.assertIsInstance(projects, list)
        self.assertGreater(len(projects), 0)

    def test_get_projects_structure(self):
        """Test that project dicts have required fields."""
        projects = get_projects()
        for project in projects:
            self.assertIn("name", project)
            self.assertIn("description", project)
            self.assertIn("link", project)
            self.assertIn("tech", project)

    def test_get_books_returns_list(self):
        """Test that get_books() returns a list."""
        books = get_books()
        self.assertIsInstance(books, list)
        self.assertGreater(len(books), 0)

    def test_get_books_structure(self):
        """Test that book dicts have required fields."""
        books = get_books()
        for book in books:
            self.assertIn("name", book)
            self.assertIn("author", book)
            self.assertIn("cover_image", book)

    def test_get_books_sorted_alphabetically(self):
        """Test that books are sorted by name."""
        books = get_books()
        book_names = [book["name"] for book in books]
        self.assertEqual(book_names, sorted(book_names))
