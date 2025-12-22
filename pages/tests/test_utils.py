from django.test import TestCase

from pages.utils import get_books


class GetBooksTest(TestCase):
    def test_get_books_returns_list(self):
        books = get_books()

        self.assertIsInstance(books, list)
        self.assertGreater(len(books), 0)

    def test_get_books_structure(self):
        books = get_books()

        for book in books:
            self.assertIn("name", book)
            self.assertIn("author", book)
            self.assertIn("cover_image", book)

            self.assertIsInstance(book["name"], str)
            self.assertIsInstance(book["author"], str)
            self.assertIsInstance(book["cover_image"], str)

    def test_get_books_sorting(self):
        books = get_books()

        names = [book["name"] for book in books]

        sorted_names = sorted(names)
        self.assertEqual(names, sorted_names)

    def test_get_books_specific_books(self):
        books = get_books()
        book_names = [book["name"] for book in books]

        self.assertIn("Permanent Record", book_names)
        self.assertIn("Principles", book_names)
        self.assertIn("Cracking the Coding Interview", book_names)

    def test_get_books_optional_fields(self):
        books = get_books()

        books_with_quotes = [book for book in books if "favourite_quote" in book]

        self.assertGreater(len(books_with_quotes), 0)

        for book in books_with_quotes:
            self.assertIsInstance(book["favourite_quote"], str)
            self.assertGreater(len(book["favourite_quote"]), 0)

    def test_get_books_cover_images(self):
        books = get_books()

        for book in books:
            cover = book["cover_image"]

            self.assertTrue(cover.startswith("images/"))

            valid_extensions = [".jpg", ".jpeg", ".png"]
            has_valid_extension = any(cover.endswith(ext) for ext in valid_extensions)
            self.assertTrue(
                has_valid_extension,
                f"Book '{book['name']}' has invalid cover image extension: {cover}",
            )

    def test_get_books_consistency(self):
        books1 = get_books()
        books2 = get_books()

        self.assertEqual(books1, books2)

    def test_get_books_no_duplicates(self):
        books = get_books()

        book_names = [book["name"] for book in books]
        unique_names = set(book_names)

        self.assertEqual(len(book_names), len(unique_names))

    def test_get_books_author_format(self):
        books = get_books()

        for book in books:
            author = book["author"]

            self.assertGreater(len(author), 0)

            self.assertEqual(author, author.strip())

    def test_get_books_known_count(self):
        books = get_books()

        self.assertEqual(len(books), 16)

    def test_get_books_edward_snowden(self):
        books = get_books()

        snowden_book = next((book for book in books if book["author"] == "Edward Snowden"), None)

        self.assertIsNotNone(snowden_book)
        self.assertEqual(snowden_book["name"], "Permanent Record")
        self.assertIn("favourite_quote", snowden_book)
        self.assertIn("Credit cards", snowden_book["favourite_quote"])

    def test_get_books_django_books(self):
        books = get_books()

        django_books = [book for book in books if "django" in book["name"].lower()]

        self.assertGreaterEqual(len(django_books), 2)

        book_names = [book["name"] for book in django_books]
        self.assertIn("Django 3 By Example", book_names)
        self.assertIn("Django For Professionals", book_names)
