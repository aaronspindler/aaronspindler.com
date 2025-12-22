from unittest.mock import mock_open, patch

from django.core.cache import cache
from django.test import Client, TestCase

from photos.tests.factories import PhotoFactory


class HealthCheckViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_check_success(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["checks"]["database"], "ok")

    @patch("pages.views.connection")
    def test_health_check_database_failure(self, mock_connection):
        mock_connection.cursor.side_effect = Exception("Database connection failed")

        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data["status"], "unhealthy")
        self.assertEqual(data["checks"]["database"], "failed")

    @patch("pages.views.cache")
    def test_health_check_cache_failure(self, mock_cache):
        mock_cache.set.side_effect = Exception("Cache unavailable")

        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["checks"]["database"], "ok")
        self.assertEqual(data["checks"]["cache"], "unavailable")


class RobotsTxtViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="User-agent: *\nDisallow: /admin/",
    )
    def test_robots_txt_serving(self, mock_file):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertIn("User-agent: *", response.content.decode())
        self.assertIn("Disallow: /admin/", response.content.decode())


class ResumeViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("pages.views.os.path.exists")
    def test_resume_disabled(self, mock_exists):
        with self.settings(RESUME_ENABLED=False):
            response = self.client.get("/resume/")

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "pages/resume_unavailable.html")

    @patch("pages.views.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"PDF content")
    def test_resume_serving_success(self, mock_file, mock_exists):
        mock_exists.return_value = True

        with self.settings(RESUME_ENABLED=True, RESUME_FILENAME="test_resume.pdf"):
            response = self.client.get("/resume/")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "application/pdf")
            self.assertIn("inline", response["Content-Disposition"])
            self.assertIn("test_resume.pdf", response["Content-Disposition"])

    @patch("pages.views.os.path.exists")
    def test_resume_file_not_found(self, mock_exists):
        mock_exists.return_value = False

        with self.settings(RESUME_ENABLED=True):
            response = self.client.get("/resume/")

            self.assertEqual(response.status_code, 404)

    @patch("pages.views.os.path.exists")
    @patch("pages.views.FileResponse")
    def test_resume_serving_error(self, mock_file_response, mock_exists):
        mock_exists.return_value = True
        mock_file_response.side_effect = Exception("Error reading file")

        with self.settings(RESUME_ENABLED=True):
            response = self.client.get("/resume/")

            self.assertEqual(response.status_code, 404)


class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

    @patch("pages.views.get_all_blog_posts")
    @patch("pages.views.get_blog_from_template_name")
    @patch("pages.views.get_books")
    def test_home_view_success(self, mock_get_books, mock_get_blog, mock_get_all_posts):
        mock_get_all_posts.return_value = [
            {"template_name": "post1", "category": "tech"},
            {"template_name": "post2", "category": "personal"},
        ]

        mock_get_blog.side_effect = [
            {
                "entry_number": "0001",
                "template_name": "post1",
                "blog_title": "Post 1",
                "category": "tech",
            },
            {
                "entry_number": "0002",
                "template_name": "post2",
                "blog_title": "Post 2",
                "category": "personal",
            },
        ]

        mock_get_books.return_value = [{"name": "Test Book", "author": "Test Author"}]

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/home.html")
        self.assertIn("blog_posts", response.context)
        self.assertIn("blog_posts_by_category", response.context)
        self.assertIn("projects", response.context)
        self.assertIn("books", response.context)

    @patch("pages.views.get_all_blog_posts")
    @patch("pages.views.get_blog_from_template_name")
    def test_home_view_caching(self, mock_get_blog, mock_get_all_posts):
        mock_get_all_posts.return_value = []
        mock_get_blog.return_value = {}

        response1 = self.client.get("/")
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(mock_get_all_posts.call_count, 1)

        response2 = self.client.get("/")
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(mock_get_all_posts.call_count, 1)  # Still 1, used cache

    def test_home_view_with_photo_albums(self):
        photo = PhotoFactory.create_photo()

        album = PhotoFactory.create_photo_album(title="Test Album", slug="test-album", is_private=False)
        album.photos.add(photo)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("album_data", response.context)
        self.assertEqual(len(response.context["album_data"]), 1)
        self.assertEqual(response.context["album_data"][0]["album"].title, "Test Album")

    def test_home_view_excludes_private_albums(self):
        photo = PhotoFactory.create_photo()

        public_album = PhotoFactory.create_photo_album(title="Public Album", slug="public", is_private=False)

        private_album = PhotoFactory.create_photo_album(title="Private Album", slug="private", is_private=True)

        public_album.photos.add(photo)
        private_album.photos.add(photo)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        album_data = response.context["album_data"]
        self.assertEqual(len(album_data), 1)
        self.assertEqual(album_data[0]["album"].title, "Public Album")

    @patch("pages.views.get_all_blog_posts")
    def test_home_view_blog_categorization(self, mock_get_all_posts):
        mock_get_all_posts.return_value = [
            {"template_name": "post1", "category": "tech"},
            {"template_name": "post2", "category": "tech"},
            {"template_name": "post3", "category": "personal"},
            {"template_name": "post4", "category": None},
        ]

        with patch("pages.views.get_blog_from_template_name") as mock_get_blog:
            mock_get_blog.side_effect = [
                {"entry_number": "0004", "template_name": "post1", "category": "tech"},
                {"entry_number": "0003", "template_name": "post2", "category": "tech"},
                {
                    "entry_number": "0002",
                    "template_name": "post3",
                    "category": "personal",
                },
                {"entry_number": "0001", "template_name": "post4", "category": None},
            ]

            response = self.client.get("/")

            self.assertEqual(response.status_code, 200)
            categories = response.context["blog_posts_by_category"]

            self.assertIn("tech", categories)
            self.assertIn("personal", categories)
            self.assertIn("uncategorized", categories)

            self.assertEqual(len(categories["tech"]), 2)
            self.assertEqual(len(categories["personal"]), 1)
            self.assertEqual(len(categories["uncategorized"]), 1)

            self.assertEqual(categories["tech"][0]["entry_number"], "0004")
            self.assertEqual(categories["tech"][1]["entry_number"], "0003")

    def test_home_view_projects_list(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        projects = response.context["projects"]

        self.assertIsInstance(projects, list)
        self.assertGreater(len(projects), 0)

        for project in projects:
            self.assertIn("name", project)
            self.assertIn("description", project)
            self.assertIn("tech", project)

    @patch("pages.views.get_books")
    def test_home_view_books_error_handling(self, mock_get_books):
        mock_get_books.side_effect = Exception("Book fetch error")

        with patch("pages.views.get_all_blog_posts", return_value=[]):
            response = self.client.get("/")

            self.assertEqual(response.status_code, 200)
